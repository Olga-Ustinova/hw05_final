import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm, CommentForm
from posts.models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_auth = User.objects.create_user('auth')
        cls.user_author = User.objects.create_user('author')
        Group(slug='slug').save()
        cls.group = Group.objects.all()[0]
        Post(author=cls.user_author, group=cls.group, text='Пост').save()
        cls.post = Post.objects.all()[0]
        Comment(author=cls.user_author, post=cls.post,
                text='Комментарий').save()
        cls.comment = Comment.objects.all()[0]

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_auth)
        self.authorized_author = Client()
        self.authorized_author.force_login(self.user_author)

    def test_create_post(self):
        """Форма создает запись в БД."""
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Новый пост',
            'group': self.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data, follow=True)
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user_auth})
        )
        self.assertEqual(Post.objects.count(), 2)
        self.assertTrue(
            Post.objects.filter(
                text='Новый пост',
                author=self.user_auth,
                group=self.group,
                image=self.post.image,
            ).exists()
        )

    def test_post_edit(self):
        """Форма редактирует существующий пост в БД."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Отредактированный пост',
            'group': self.group.pk,
        }
        response = self.authorized_author.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                author=self.post.author,
                group=self.group,
                pk=self.post.pk,
            ).exists()
        )

    def test_add_comment(self):
        """Форма создает комментарий к посту в БД."""
        form_data = {
            'text': 'Комментарий',
        }
        response = self.authorized_author.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.pk}),
            data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:post_detail',
                              kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(Comment.objects.count(), 2)
        self.assertTrue(
            Comment.objects.filter(
                text=form_data['text'],
                author=self.post.author,
                post=self.post,
            ).exists()
        )

    def test_field_label_end_help_text_post(self):
        self.form_1 = PostForm()
        field_label_text = self.form_1.fields['text'].label
        self.assertEqual(field_label_text, 'Текст поста')
        field_label_group = self.form_1.fields['group'].label
        self.assertEqual(field_label_group, 'Группа')
        field_label_image = self.form_1.fields['image'].label
        self.assertEqual(field_label_image, 'Изображение')

        field_help_text_text = self.form_1.fields['text'].help_text
        self.assertEqual(
            field_help_text_text, 'Текст нового поста'
        )
        field_help_text_group = self.form_1.fields['group'].help_text
        self.assertEqual(field_help_text_group,
                         'Группа, к которой будет относиться пост')
        field_help_text_image = self.form_1.fields['image'].help_text
        self.assertEqual(field_help_text_image,
                         'Изображение, которое будет относиться к посту')

    def test_field_label_end_help_text_comment(self):
        self.form_2 = CommentForm()
        field_label_text_comment = self.form_2.fields['text'].label
        field_help_text_text_comment = self.form_2.fields['text'].help_text
        self.assertEqual(field_label_text_comment, 'Текст комментария')
        self.assertEqual(
            field_help_text_text_comment, 'Введите комментарий к посту'
        )
