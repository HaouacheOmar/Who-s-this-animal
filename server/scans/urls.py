from rest_framework.routers import SimpleRouter

from .views import ScanViewSet

router = SimpleRouter()
router.register("scans", ScanViewSet, basename="scan")
urlpatterns = router.urls
