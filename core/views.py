from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Post, Topic, Comment, Like, Friendship
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

@login_required
def home(request):
    q = request.GET.get('q') if request.GET.get('q') != None else ''

    # 1. Get a list of the user's friends
    # We query where the status is 'accepted' from either side of the relationship
    friends_sent = Friendship.objects.filter(from_user=request.user, status='accepted').values_list('to_user_id', flat=True)
    friends_received = Friendship.objects.filter(to_user=request.user, status='accepted').values_list('from_user_id', flat=True)
    friend_ids = list(friends_sent) + list(friends_received)

    # 2. Include the user's own ID
    allowed_user_ids = friend_ids + [request.user.id]

    # Optimized query using select_related and prefetch_related
    posts = Post.objects.filter(
        author__id__in=allowed_user_ids
    ).filter(
        Q(topic__name__icontains=q)|
        Q(caption__icontains=q)
    ).select_related('author', 'topic').prefetch_related('likes')

    topics = Topic.objects.all()[0:5]
    post_count = posts.count()
    # This comment query would also need to be restricted
    post_comments = Comment.objects.filter(post__in=posts)

    # For activity feed, let's show comments on posts the user can see
    post_comments = Comment.objects.filter(
        post__in=posts).select_related('author', 'post').order_by('-created_at')[:5]

    context = {'posts':posts, 'topics': topics, 'post_count': post_count,
                'post_comments': post_comments}
    return render(request, 'core/home.html', context)

def post(request,pk):
    # Use prefetch_related for efficiency even on a single object
    post = get_object_or_404(Post.objects.prefetch_related(
        'comments__author', 'likes'
    ), id=pk)
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

    # Friendship status logic
    friendship_status = None
    if request.user.is_authenticated and request.user != user:
        # Check if a request was sent from the logged-in user to the profile user
        sent_request = Friendship.objects.filter(from_user=request.user, to_user=user).first()
        # Check if a request was received by the logged-in user from the profile user
        received_request = Friendship.objects.filter(from_user=user, to_user=request.user).first()

        if sent_request:
            friendship_status = sent_request.status
        elif received_request:
            # If a request was received, show its status but give options to accept/decline
            friendship_status = received_request.status
            if received_request.status == 'pending':
                friendship_status = 'received_pending' # A custom status for the template

    posts = user.post_set.all().prefetch_related('likes')
    post_comments = user.comment_set.all()
    topics = Topic.objects.all()
    context = {'user': user, 'posts': posts, 'post_comments': post_comments, 'topics': topics, 'friendship_status': friendship_status}
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

@login_required(login_url='login')
def like_post(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(Post, id=post_id)
        like, created = Like.objects.get_or_create(user=request.user, post=post)

        if not created:
            # If the like already existed, delete it (unlike).
            like.delete()
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required(login_url='login')
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    if request.user != to_user:
        # Prevent creating a duplicate request if one already exists (from either user)
        Friendship.objects.get_or_create(from_user=request.user, to_user=to_user)
    return redirect('user-profile', pk=user_id)

@login_required(login_url='login')
def manage_friend_request(request, user_id, action):
    from_user = get_object_or_404(User, id=user_id)
    friend_request = get_object_or_404(Friendship, from_user=from_user, to_user=request.user)

    if action == 'accept':
        friend_request.status = 'accepted'
        friend_request.save()
        # Optional: Create a reciprocal friendship for easier querying
        Friendship.objects.get_or_create(from_user=request.user, to_user=from_user, defaults={'status': 'accepted'})
    elif action == 'decline':
        friend_request.delete() # Or set status to 'declined' if you want to keep the record

    return redirect('user-profile', pk=user_id)

@login_required(login_url='login')
def remove_friend(request, user_id):
    friend_to_remove = get_object_or_404(User, id=user_id)
    # Delete the friendship records from both sides
    Friendship.objects.filter(from_user=request.user, to_user=friend_to_remove).delete()
    Friendship.objects.filter(from_user=friend_to_remove, to_user=request.user).delete()
    return redirect('user-profile', pk=user_id)

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