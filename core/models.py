from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    bio = models.TextField(blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', default='profile_pics/default.jpg')
    cover_photo = models.ImageField(upload_to='cover_photos/', blank=True)
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

class Topic(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return str(self.name)

class Post(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    topic = models.ForeignKey(Topic, on_delete=models.SET_NULL, null=True)
    caption = models.TextField()
    photo = models.ImageField(upload_to='post_photos/', blank=True, null=True)
    latitude = models.DecimalField(max_digits=99, decimal_places=15, null=True, blank=True)
    longitude = models.DecimalField(max_digits=99, decimal_places=15, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Post by {self.author.username} at {self.created_at.strftime("%Y-%m-%d %H:%M")}'

class Comment(models.Model):
    post = models.ForeignKey(Post, related_name='comments', on_delete=models.CASCADE)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Show oldest comments first

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post}'

class Like(models.Model):
    post = models.ForeignKey(Post, related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only like a post once
        unique_together = ('post', 'user')

    def __str__(self):
        return f'{self.user.username} likes {self.post}'
