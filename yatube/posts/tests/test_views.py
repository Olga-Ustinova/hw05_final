import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms

from posts.models import Follow, Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user('author')
        cls.user_auth = User.objects.create_user('auth')
        Group(slug='slug').save()
        cls.group = Group.objects.all()[0]
        Post(author=cls.user_author, group=cls.group, text='Пост').save()
        cls.post = Post.objects.all()[0]
        Comment(author=cls.user_author, post=cls.post,
                text='Комментарий').save()
        cls.comment = Comment.objects.all()[0]

        cls.templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': cls.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': cls.post.author}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': cls.post.pk}):
                'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/post_create.html',
            reverse('posts:post_edit', kwargs={'post_id': cls.post.pk}):
                'posts/post_create.html',
            reverse('posts:follow_index'): 'posts/follow.html',
        }
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user_author)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for reverse_name, template in self.templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_pages_forms_show_context_with_fields_text_and_group(self):
        """Страницы создания и редоктирования поста передаются с правильным
        заголовком, текстом, постами, объектами страниц."""
        response_post_create = self.authorized_author.get(
            reverse('posts:post_create')
        )
        response_post_edit = self.authorized_author.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk})
        )
        form_fields = {
            ('text', forms.fields.CharField, response_post_create),
            ('group', forms.fields.ChoiceField, response_post_create),
            ('image', forms.fields.ImageField, response_post_create),
            ('text', forms.fields.CharField, response_post_edit),
            ('group', forms.fields.ChoiceField, response_post_edit),
            ('image', forms.fields.ImageField, response_post_edit)
        }
        for value, expected, response in form_fields:
            with self.subTest(value=value, response=response):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_index_page_url_contains_post(self):
        """Содержимое текста и изображения главной страницы
        соответствуют ожиданиям. Создав пост (см `setUp`),
        увидим его на главной странице."""
        response = self.authorized_author.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        post_text_0 = first_object.text
        post_image_0 = first_object.image
        self.assertEqual(post_text_0, 'Пост')
        self.assertEqual(post_image_0, self.post.image)

    def test_post_detail_page_url_contains_post(self):
        """Страница с одним постом, отфильтрованным по id, сформирована с
        правильным текстом, автором, заголовком,
        названием и описанием группы."""
        response = self.authorized_author.get(
            reverse('posts:post_detail',
                    kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(response.context['post'].text, self.post.text)
        self.assertEqual(response.context['post'].author,
                         self.user_author)
        self.assertEqual(response.context['post'].group.title,
                         self.group.title)
        self.assertEqual(response.context['post'].group.slug, self.group.slug)
        self.assertEqual(response.context['post'].group.description,
                         self.group.description)
        self.assertEqual(response.context['post'].image, self.post.image)

    def test_post_added_correctly(self):
        """Пост на главной странице сайта, на странице выбранной группы и
        в профайле пользователя добавлен корректно."""
        response_index = self.authorized_author.get(reverse('posts:index'))
        response_group_list = self.authorized_author.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        response_profile = self.authorized_author.get(
            reverse('posts:profile', kwargs={'username': self.post.author})
        )
        response_pages = [response_index, response_group_list,
                          response_profile, ]
        for response in response_pages:
            with self.subTest(response=response):
                self.assertIn(self.post, response.context['page_obj'])

    def test_comment_added_on_post_page_correctly(self):
        """После успешной отправки комментарий появляется на странице поста."""
        response = self.authorized_author.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.pk}))
        self.assertIn(self.comment, response.context['comments'])

    def test_cache_index(self):
        """При удалении записи из базы, она остаётся в response.content
        главной страницы до тех пор, пока кэш не будет очищен принудительно."""
        response_1 = self.client.get(reverse('posts:index'))
        Post.objects.all().delete()
        response_2 = self.client.get(reverse('posts:index'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.client.get(reverse('posts:index'))
        self.assertNotEqual(response_1.content, response_3.content)

    def test_authorized_user_can_follow_other_users(self):
        """Авторизованный пользователь может подписываться
        на других пользователей."""
        self.authorized_author.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.user_auth})
        )
        self.assertTrue(Follow.objects.filter(
            user=self.user_author, author=self.user_auth).exists())

    def test_authorized_user_can_unfollow_other_users(self):
        """Авторизованный пользователь может отписаться
        от других пользователей."""
        self.authorized_author.get(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.user_author})
        )
        self.assertFalse(Follow.objects.all())

    def test_post_in_subscriber_feed(self):
        """Новая запись пользователя появляется в ленте тех,
        кто на него подписан."""
        Follow.objects.create(user=self.user_author, author=self.user_auth)
        Post.objects.create(author=self.user_auth, text='Пост')
        response = self.authorized_author.get(reverse('posts:follow_index'))
        self.assertEqual(response.context['page_obj'][0].author,
                         self.user_auth)

    def test_post_is_not_in_the_feed(self):
        """Новая запись пользователя не появляется в ленте тех,
        кто на него не подписан."""
        response = self.authorized_author.get(reverse('posts:follow_index'))
        self.assertNotIn(self.post, response.context['page_obj'])


class PaginatorViewsTest(TestCase):
    def setUp(self):
        self.user_auth = User.objects.create_user('auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_auth)
        self.group = Group.objects.create(
            title='Группа',
            slug='slug',
        )
        Post.objects.bulk_create(
            [Post(author=self.user_auth,
                  text='Пост',
                  group=self.group,
                  image='posts/small.gif')
                for _ in range(13)]
        )

    def test_first_page_contains_ten_records(self):
        """Количество постов на первой странице равно 8."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 8)

    def test_second_page_contains_three_records(self):
        """Количество постов на второй странице должно быть 2 поста."""
        response = self.authorized_client.get(
            reverse('posts:index') + '?page=2'
        )
        self.assertEqual(len(response.context['page_obj']), 2)
