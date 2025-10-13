from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from .models import Post, Topic, Comment
from .forms import PostForm, UserForm
from django.http import JsonResponse
from django.utils.timesince import timesince
from django.utils import timezone

def loginPage(request):

    page = 'login'

    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        username = request.POST.get('username').lower()
        password = request.POST.get('password')

        try:
            user = User.objects.get(username=username)
        except:
            messages.error(request, "User does not exist")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Username OR password does not exist")

    context={'page': page}
    return render(request, 'core/login_register.html', context)

def logoutUser(request):
    logout(request)
    return redirect('home')

def registerPage(request):
    form = UserCreationForm()

    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.username = user.username.lower()
            user.save()
            login(request,user)
            return redirect('home')
        else:
            messages.error(request, 'An error occurred during regisretion.')
    return render(request, 'core/login_register.html',  {'form': form})

def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    posts = Post.objects.filter(
        Q(topic__name__icontains=q)|
        Q(caption__icontains=q)
    )

    topics = Topic.objects.all()[0:5]
    post_count = posts.count()
    post_comments = Comment.objects.all().filter(Q(post__topic__name__icontains=q))


    context = {'posts':posts, 'topics': topics, 'post_count': post_count,
                'post_comments': post_comments}
    return render(request, 'core/home.html', context)

def post(request,pk):
    post = Post.objects.get(id=pk)
    post_comments = post.comments.all()

    if request.method == 'POST':
        Comment.objects.create(
            author = request.user,
            post = post,
            text = request.POST.get('text')
        )
        return redirect('post', pk=post.id)

    context = {'post': post, 'post_comments': post_comments,} 
    return render(request, 'core/post.html', context)

def userProfile(request, pk):
    user = User.objects.get(id=pk)
    posts = user.post_set.all()
    post_comments = user.comment_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'posts': posts, 'post_comments': post_comments,
               'topics': topics}
    return render(request, 'core/profile.html', context)

@login_required(login_url='login')
def createPost(request):
    form = PostForm()
    topics = Topic.objects.all()
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            topic_name = request.POST.get('topic')
            topic, _ = Topic.objects.get_or_create(name=topic_name)
            post.topic = topic
            post.save()
            return redirect('home')
        

    context = {'form': form, 'topics': topics}
    return render(request, 'core/post_form.html', context)

@login_required(login_url='login')
def updatePost(request, pk):
    post = Post.objects.get(id=pk)
    form = PostForm(instance=post)
    topics = Topic.objects.all()
    if request.user != post.author:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            post = form.save(commit=False)
            topic_name = request.POST.get('topic')
            topic, _ = Topic.objects.get_or_create(name=topic_name)
            post.topic = topic
            post.save()
            return redirect('home')
        
    context = {'form': form, 'topics': topics, 'post': post}
    return render(request, 'core/post_form.html', context)

@login_required(login_url='login')
def deletePost(request, pk):
    post = Post.objects.get(id=pk)

    if request.user != post.author:
        return HttpResponse('You are not allowed here!!')

    if request.method == 'POST':
        post.delete()
        return redirect('home')
    return render(request, 'core/delete.html', {'obj':post})

def map_page_view(request):
    """
    This view just renders the map page template. The actual
    post data will be fetched by a separate API view.
    """
    # We'll also pass the current location for the initial map view.
    # For now, we'll hardcode it to Hsinchu, Taiwan.
    context = {
        'initial_lat': 24.8138,
        'initial_lon': 120.9675,
    }
    return render(request, 'core/map_page.html', context)

def get_all_posts_api(request):
    """
    This is an API endpoint that returns all posts as JSON.
    The frontend JavaScript will call this URL to get the pin data.
    """
    posts = Post.objects.filter(
        latitude__isnull=False, longitude__isnull=False
    ).select_related('author', 'topic').annotate(
        comments_count=Count('comments')
    )

    now = timezone.now()
    # Create a list of dictionaries, with each dictionary representing a post.
    post_data = [
        {
            "id": post.id,
            "author": post.author.username,
            "author_id": post.author.id,
            "caption": post.caption,
            "topic": post.topic.name,
            "comments_count": post.comments_count,
            "created_ago": timesince(post.created_at, now) + " ago",
            "photo_url": post.photo.url if post.photo else '',
            "lat": post.latitude,
            "lon": post.longitude
        }
        for post in posts
    ]

    return JsonResponse(post_data, safe=False)