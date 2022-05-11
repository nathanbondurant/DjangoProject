from django.shortcuts import render, redirect
from .forms import PostForm,ProfileForm, RelationshipForm
from .models import Post, Comment, Like, Profile, Relationship
from datetime import datetime, date

from django.contrib.auth.decorators import login_required
from django.http import Http404


# Create your views here.

# When a URL request matches the pattern we just defined, 
# Django looks for a function called index() in the views.py file. 

def index(request):
    """The home page for Learning Log."""
    return render(request, 'FeedApp/index.html')



@login_required #prevents unauthorized access 
def profile(request):
    profile = Profile.objects.filter(user=request.user) #use filter to get the profile of the person who is logged in
    if not profile.exists(): #checks if profile exists
        Profile.objects.create(user=request.user)
    profile = Profile.objects.get(user=request.user) #get is the same as filter

    if request.method != 'POST': #if you are updating the profile, you get the specific instance
        form = ProfileForm(instance=profile)
    else:
        form = ProfileForm(instance=profile,data=request.POST) #gets the form or attributes
        if form.is_valid():
            form.save()
            return redirect('FeedApp:profile')

    context= {'form': form}
    return render(request, 'FeedApp/profile.html', context)

@login_required
def myfeed(request):
    comment_count_list= []
    like_count_list = []
    posts= Post.objects.filter(username=request.user).order_by('-date_posted') #gets my feed and orders it
    for p in posts:
        c_count = Comment.objects.filter(post=p).count() #gets the comment count for a specific post
        l_count = Like.objects.filter(post=p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list, like_count_list) #so you can iterate through all at once

    context= {'posts':posts, 'zipped_list':zipped_list}
    return render(request, 'FeedApp/myfeed.html', context)

@login_required
def new_post(request):
    if request.method != 'POST':
        form = PostForm() #gets the blank form
    else:
        form = PostForm(request.POST,request.FILES)
        if form.is_valid():
            new_post=form.save(commit=False) #saves but doesn't commit to the database
            new_post.username = request.user #assigns to a user
            new_post.save()
            return redirect('FeedApp:myfeed')
    context = {'form':form}
    return render(request, 'FeedApp/new_post.html', context)

@login_required
def friendsfeed(request):
    comment_count_list = []
    like_count_list = []
    friends = Profile.objects.filter(user=request.user).values('friends') #specifies for the user and their friends
    posts = Post.objects.filter(username__in=friends).order_by('-date_posted')
    for p in posts:
        c_count = Comment.objects.filter(post=p).count()
        l_count = Like.objects.filter(post=p).count()
        comment_count_list.append(c_count)
        like_count_list.append(l_count)
    zipped_list = zip(posts,comment_count_list,like_count_list)

    if request.method == 'POST' and request.POST.get("like"): #checks to see if like button was clicked
        post_to_like = request.POST.get("like") #gives the button name and know it was pressed
        print(post_to_like)
        like_already_exists = Like.objects.filter(post_id=post_to_like,username=request.user) #checks to see if the same user and post was liked
        if not like_already_exists.exists():
            Like.objects.create(post_id=post_to_like,username=request.user)
            return redirect("FeedApp:friendsfeed")

    context = {'posts':posts, 'zipped_list':zipped_list}
    return render(request, 'FeedApp/friendsfeed.html', context)


@login_required
def comments(request, post_id): 
    if request.method == 'POST' and request.POST.get("btn1"): #checks if it was clicked
        comment = request.POST.get("comment") #returns what is in the box
        Comment.objects.create(post_id=post_id, username=request.user, text=comment, date_added=date.today())
    
    #retreives comments from database for specific post
    comments= Comment.objects.filter(post=post_id)
    post= Post.objects.get(id=post_id)
    context = {'post':post, 'comments':comments}

    return render(request, 'FeedApp/comments.html', context)

@login_required
def friends(request):
    #get the admin profile and user profile to create the first relationship
    admin_profile = Profile.objects.get(user=1) #admin is user 1
    user_profile = Profile.objects.get(user=request.user)

    #to get friends list
    user_friends = user_profile.friends.all()
    user_friends_profiles = Profile.objects.filter(user__in=user_friends) #gets profile for these friends

    #get sent freind requests
    user_relationships = Relationship.objects.filter(sender=user_profile)
    request_sent_profiles = user_relationships.values('receiver')

    #shows all non-freinds (excludes those who have been sent requests)
    all_profiles = Profile.objects.exclude(user=request.user).exclude(id__in=user_friends_profiles).exclude(id__in=request_sent_profiles)
    #shows received requests
    request_received_profiles = Relationship.objects.filter(receiver=user_profile,status='sent')

    #creates first relationship if doesn't already exist
    if not user_relationships.exists(): #filter works with exists
        Relationship.objects.create(sender=user_profile,receiver=admin_profile,status='sent')

    #sees which button was pressed (send or accept)
    if request.method == 'POST' and request.POST.get("send_requests"):
        receivers = request.POST.getlist("send_requests")
        for receiver in receivers:
            receiver_profile = Profile.objects.get(id=receiver) #gets their profile
            Relationship.objects.create(sender=user_profile,receiver=receiver_profile,status='sent')
        return redirect('FeedApp:friends')

    if request.method == 'POST' and request.POST.get("receive_requests"):
        senders = request.POST.getlist("receive_requests") #get a list of senders who sent us a request
        for sender in senders: 
            Relationship.objects.filter(id=sender).update(status='accepted') #accepts the rrequest

            relationship_obj = Relationship.objects.get(id=sender)
            user_profile.friends.add(relationship_obj.sender.user) #adds the new friend to freind's list
            relationship_obj.sender.friends.add(request.user) #add to their profile

    context = {'user_friends_profiles':user_friends_profiles,'user_relationships':user_relationships,
                    'all_profiles':all_profiles, 'request_received_profiles':request_received_profiles}
    
    return render(request, 'FeedApp/friends.html', context)