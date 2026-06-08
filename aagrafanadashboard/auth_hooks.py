from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import urls


class GrafanaDashboardMenuItem(MenuItemHook):
    def __init__(self):
        super().__init__(
            text=_("Statistics"),
            classes="fas fa-chart-line",
            url_name="aagrafanadashboard:index",
            navactive=["aagrafanadashboard:"],
        )

    def render(self, request):
        if request.user.has_perm("aagrafanadashboard.can_view_grafana_statistics"):
            return super().render(request)
        return ""


@hooks.register("menu_item_hook")
def register_menu():
    return GrafanaDashboardMenuItem()


@hooks.register("url_hook")
def register_urls():
    return UrlHook(urls, "aagrafanadashboard", r"^statistics/")
