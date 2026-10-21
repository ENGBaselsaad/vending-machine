from django.urls import path

from . import api, views

urlpatterns = [
    path("", views.customer_page, name="customer"),
    path("manage/", views.admin_page, name="manage"),
    path("api/machine/", api.machine_state, name="api-machine"),
    path("api/machine/insert-coin/", api.insert_coin, name="api-insert"),
    path("api/machine/select/", api.select_product, name="api-select"),
    path("api/machine/cancel/", api.cancel, name="api-cancel"),
    path("api/admin/", api.admin_state, name="api-admin"),
    path("api/admin/products/", api.admin_create_product, name="api-admin-create-product"),
    path(
        "api/admin/products/<int:product_id>/",
        api.admin_update_product,
        name="api-admin-update-product",
    ),
    path(
        "api/admin/products/<int:product_id>/restock/",
        api.admin_restock_product,
        name="api-admin-restock-product",
    ),
    path(
        "api/admin/coins/<str:denomination>/restock/",
        api.admin_restock_coin,
        name="api-admin-restock-coin",
    ),
]
