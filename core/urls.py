from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.loginPage, name="login"),
    path('logout/', views.logoutUser, name="logout"),
    path('register/', views.registerPage, name="register"),

    path('', views.home, name="home"),
    path('post/<int:pk>/', views.post, name="post"),
    path('profile/<int:pk>/', views.userProfile, name="user-profile"),

    path('create-post/', views.createPost, name="create-post"),
    path('update-post/<int:pk>/', views.updatePost, name="update-post"),
    path('delete-post/<int:pk>/', views.deletePost, name="delete-post"),

    # URL for the like/unlike functionality
    path('post/<int:post_id>/like/', views.like_post, name='like_post'),

    path('map/', views.map_page_view, name='map-page'),
    path('api/posts/', views.get_all_posts_api, name='api-get-posts'),
]
 