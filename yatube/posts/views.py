from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .models import Follow, Group, Post, User
from .forms import PostForm, CommentForm


def paginator(request, posts):
    paginator = Paginator(posts, settings.SELECT_LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    title = 'Последние обновления на сайте'
    text = 'Последние обновления на сайте'
    posts = Post.objects.select_related('author', 'group')[:10]
    page_obj = paginator(request, posts)
    context = {
        'title': title,
        'text': text,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    title = f'Записи сообщества {group.title}'
    text = f'{group.title}'
    text_group = f'{group.description}'
    posts = group.posts.select_related('author')[:10]
    page_obj = paginator(request, posts)
    context = {
        'group': group,
        'title': title,
        'text': text,
        'text_group': text_group,
        'posts': posts,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    title = f'Профайл пользователя: {author.get_full_name()}'
    posts = author.posts.select_related('group')
    posts_count = posts.count()
    page_obj = paginator(request, posts)
    following = (request.user.is_authenticated) and (
        request.user != author) and Follow.objects.filter(
        user=request.user, author=author).exists()
    context = {
        'author': author,
        'title': title,
        'posts': posts,
        'posts_count': posts_count,
        'page_obj': page_obj,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = post.comments.all()
    posts = Post.objects.select_related('author')
    posts_count = posts.count()
    page_obj = paginator(request, posts)
    context = {
        'post': post,
        'posts_count': posts_count,
        'page_obj': page_obj,
        'form': form,
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    # передаем POST если он есть, иначе None
    form = PostForm(request.POST or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', post.author)
    context = {
        'form': form,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user != post.author:
        return redirect('posts:post_detail', post_id)
    form = PostForm(request.POST or None,
                    files=request.FILES or None, instance=post)
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id)
    return render(request, 'posts/post_create.html',
                  {'form': form, 'is_edit': True})


@login_required
def add_comment(request, post_id):
    # Получаем пост и сохраняем его в переменную post.
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post = Post.objects.filter(author__following__user=request.user)
    page_obj = paginator(request, post)
    context = {'page_obj': page_obj}
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:profile', username=author.username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username=author.username)
