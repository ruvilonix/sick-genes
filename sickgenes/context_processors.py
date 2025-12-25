from .models import SiteConfiguration

def site_config(request):
    return {
        'site_config': SiteConfiguration.get_solo()
    }