from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_auth = User.objects.create_user('auth')
        cls.user_author = User.objects.create_user('author')
        Group(slug='slug').save()
        cls.group = Group.objects.all()[0]
        Post(author=cls.user_author, group=cls.group, text='Пост').save()
        cls.post = Post.objects.all()[0]
        cls.status_code_url_names = {
            '/': 200,
            f'/group/{cls.group.slug}/': 200,
            f'/profile/{cls.post.author}/': 200,
            f'/posts/{cls.post.pk}/': 200,
            '/unexisting_page/': 404,
        }
        cls.templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{cls.group.slug}/': 'posts/group_list.html',
            f'/profile/{cls.post.author}/': 'posts/profile.html',
            f'/posts/{cls.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/post_create.html',
            f'/posts/{cls.post.pk}/edit/': 'posts/post_create.html',
            '/follow/': 'posts/follow.html',
        }

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostURLTests.user_auth)
        self.authorized_author = Client()
        self.authorized_author.force_login(PostURLTests.user_author)

    def test_urls_exists_at_desired_location(self):
        """Неавторизованный пользователь видит страницы."""
        for address, status_code in self.status_code_url_names.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, status_code)

    def test_post_create_url_redirect_anonymous_on_auth__login(self):
        """При создании поста анонимный пользователь
        перенаправляется на страницу логина."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_url_redirect_anonymous_on_auth_login(self):
        """При редактировании поста анонимный пользователь
        перенаправляется на страницу логина."""
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.pk}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            (f'/auth/login/?next=/posts/{PostURLTests.post.pk}/edit/')
        )

    def test_comment_url_redirect_anonymous_on_auth_login(self):
        """Комментировать посты может только авторизованный пользователь."""
        response = self.guest_client.get(
            f'/posts/{PostURLTests.post.pk}/comment/',
            follow=True
        )
        self.assertRedirects(
            response,
            (f'/auth/login/?next=/posts/{PostURLTests.post.pk}/comment/')
        )

    def test_post_create_url_exists_at_desired_location_authorized(self):
        """Страница создания поста доступна
        авторизированному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, 200)

    def test_post_edit_url_redirect_on_post_detail_authorized(self):
        """При редактировании поста авторизованный пользователь
        перенаправляется на страницу поста."""
        response = self.authorized_client.get(
            f'/posts/{PostURLTests.post.pk}/edit/',
            follow=True
        )
        self.assertRedirects(response, (f'/posts/{PostURLTests.post.pk}/'))

    def test_post_edit_url_exists_at_desired_location_authorized(self):
        """Автору доступна страница редактирования поста."""
        response = self.authorized_author.get(
            f'/posts/{PostURLTests.post.pk}/edit/'
        )
        self.assertEqual(response.status_code, 200)

    def test_unexisting_page_at_desired_location(self):
        """Несуществующая страница выдаст ошибку."""
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, 404)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for address, template in self.templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_author.get(address)
                self.assertTemplateUsed(response, template)


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_homepage(self):
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, 200)
