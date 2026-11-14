"""
Gene Search: turn a list of search terms into matched genes.

Used by the public Gene Search page and the staff "Add genes" page, which
share one template (molecule_match.html).

Nothing is stored between requests. Each time the form is submitted, the page
sends back every term it is showing, plus what the user did to them:

    term            one per row on the page (hidden input)
    search_terms    the text box: new terms, one per line
    remove          a ticked Remove box; its value is that row's term
    fix:<term>      the text typed into a "Not found" row, to correct the term
    choice:<term>   the gene ID picked in a "Several matches" dropdown

Every term is then searched again and the results are sorted into the page's
three tables: matched, several matches and not found. Searching is one batch
of queries however many terms there are, so repeating it is cheap.
"""

# Longer lists make very large pages, so they're refused
MAX_SEARCH_TERMS = 5000


def search_context(post, model):
    """
    Template context for the search page, built from the submitted form.

    On a first visit `post` is empty, which gives an empty page.
    """
    terms = terms_on_page(post)
    new_terms = clean(post.get('search_terms', '').splitlines())

    context = {'error': '', 'search_text': ''}
    if len(terms) + len(new_terms) > MAX_SEARCH_TERMS:
        # Leave the new terms out, but keep them in the text box for editing
        context['error'] = (
            f'Please search at most {MAX_SEARCH_TERMS:,} terms at a time '
            f'(this would make {len(terms) + len(new_terms):,}).'
        )
        context['search_text'] = post['search_terms']
    else:
        terms += new_terms

    # dict.fromkeys drops repeated terms and keeps the order
    context.update(sort_into_tables(model, list(dict.fromkeys(terms)), post))
    return context


def terms_on_page(post):
    """The terms of the rows the user kept, with corrections applied."""
    removed = set(post.getlist('remove'))
    kept = [term for term in post.getlist('term') if term not in removed]
    return clean(post.get(f'fix:{term}', term) for term in kept)


def clean(strings):
    """Strip spaces and drop blanks."""
    return [string.strip() for string in strings if string.strip()]


def sort_into_tables(model, terms, post):
    """Search for every term and sort the results into the page's three tables."""
    results = model.objects.find_matching_items(terms)

    # Keyed by item ID, so an item found by two terms is listed once
    matched = {
        result['item'].id: matched_row(result['search_string'], result['item'], chosen=False)
        for result in results['one_match']
    }

    several = []
    for result in results['multiple_matches']:
        term, items = result['search_string'], result['items']
        chosen_item = find_by_id(items, post.get(f'choice:{term}'))
        if chosen_item:
            matched[chosen_item.id] = matched_row(term, chosen_item, chosen=True)
        else:
            several.append({
                'term': term,
                'options': [(item.id, item_label(item)) for item in items],
                'preselected': exact_match_id(term, items),
            })

    return {
        'matched': list(matched.values()),
        'several': several,
        'not_found': results['no_matches'],
        # True when there's nothing left for the user to correct or choose
        'all_matched': bool(matched) and not several and not results['no_matches'],
    }


def matched_row(term, item, chosen):
    """
    A row of the "Matched" table.

    `chosen` marks a term that matches several items, where the user picked
    this one. The page sends that choice back so it isn't asked again.
    """
    return {'term': term, 'item': item, 'label': item_label(item), 'chosen': chosen}


def find_by_id(items, item_id):
    """The item with this ID (a string from the form), or None."""
    for item in items:
        if str(item.id) == item_id:
            return item
    return None


def exact_match_id(term, items):
    """The ID of the item named exactly like the term, to preselect in the dropdown."""
    for item in items:
        if str(item).lower() == term.lower():
            return item.id
    return None


def item_label(item):
    """Label for an item, e.g. "TRH – thyrotropin releasing hormone"."""
    name = getattr(item, 'name', None)
    if name and name != str(item):
        return f'{item} – {name}'
    return str(item)


def matched_item_ids(context):
    return [row['item'].id for row in context['matched']]
