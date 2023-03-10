from django.contrib.auth import get_user_model
from django.test import TestCase

from posts.models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):

    def test_models_post_and_group_have_correct_object_names(self):
        post = Post(text="Короткий пост")
        self.assertEqual(str(post), "Короткий пост")

        long_post = Post(text="Не более 15 символов может уместиться в превью")
        self.assertEqual(str(long_post), "Не более 15 сим")

        group = Group(title="Записи сообщества")
        self.assertEqual(str(group), "Записи сообщества")
