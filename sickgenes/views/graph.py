import random
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Count, Q
from sickgenes.models import HgncGene, StringInteraction


def gene_network_data(request):
    """
    API view to generate data for a Sigma.js graph.

    This view expects a GET request with a 'disease_ids' parameter,
    which can contain one or more disease IDs.

    Example GET request: /api/graph-data/?disease_ids=1&disease_ids=5

    It returns a JSON object with 'nodes' and 'edges':
    - Nodes: Genes found in studies for ALL specified diseases.
      - 'size' attribute corresponds to the number of unique studies the gene was found in.
    - Edges: STRING DB interactions between the identified genes.
      - 'size' attribute corresponds to the 'combined_score'.
    """
    disease_ids_str = request.GET.getlist('disease_ids')
    if not disease_ids_str:
        return JsonResponse({'error': 'Please provide at least one disease ID.'}, status=400)

    try:
        # Convert all provided IDs to integers and remove duplicates
        disease_ids = list(set(int(id) for id in disease_ids_str))
        num_diseases = len(disease_ids)

    except ValueError:
        return JsonResponse({'error': 'Invalid disease ID provided.'}, status=400)
    
    confidence_threshold = request.GET.get('confidence_threshold', 700)

    # 2. Find genes associated with ALL specified diseases
    # We annotate each gene with two counts:
    #  - disease_count: How many of the *input diseases* this gene is linked to.
    #  - study_count: How many *unique studies* this gene is linked to (across those diseases).
    # Then, we filter for genes where disease_count matches the number of diseases we're looking for.
    common_genes_qs = HgncGene.objects.filter(
        genefinding__study_cohort__disease_tags__id__in=disease_ids
    ).annotate(
        disease_count=Count(
            'genefinding__study_cohort__disease_tags',
            filter=Q(genefinding__study_cohort__disease_tags__id__in=disease_ids),
            distinct=True
        ),
        study_count=Count('genefinding__study_cohort__study', distinct=True)
    ).filter(
        disease_count=num_diseases
    )

    # 3. Prepare nodes for Sigma.js
    nodes = []
    # We need a quick lookup of gene IDs for the next step
    common_gene_pks = []
    
    # Assuming your HgncGene model has a 'symbol' field for the gene name
    for gene in common_genes_qs:
        nodes.append({
            'key': gene.symbol,  # Use a unique, readable identifier
            'label': gene.symbol,
            'x': random.random(), # Assign random coordinates for initial layout
            'y': random.random(),
            'size': gene.study_count, # Size node by study count
            'type': 'circle'
        })
        common_gene_pks.append(gene.pk)

    # 4. Find interactions (edges) between these common genes
    edges = []
    if common_gene_pks:
        interactions = StringInteraction.objects.filter(
            protein1__hgnc_gene_id__in=common_gene_pks,
            protein2__hgnc_gene_id__in=common_gene_pks,
            combined_score__gte=confidence_threshold,
        ).select_related('protein1__hgnc_gene', 'protein2__hgnc_gene')

        for interaction in interactions:
            # Ensure the source/target IDs match the node IDs
            source_gene_symbol = interaction.protein1.hgnc_gene.symbol
            target_gene_symbol = interaction.protein2.hgnc_gene.symbol
            
            # Avoid self-loops if they exist and only add edges for nodes in our graph
            if source_gene_symbol != target_gene_symbol:
                 edges.append({
                    'key': f'e{interaction.id}',
                    'source': source_gene_symbol,
                    'target': target_gene_symbol,
                    'size': interaction.combined_score,
                    'type': 'line',
                    'color': '#ccc'
                })

    # 5. Combine and return as JSON
    graph_data = {'nodes': nodes, 'edges': edges}
    return JsonResponse(graph_data)

def graph_display(request):
    return render(request, 'sickgenes/network_display.html')