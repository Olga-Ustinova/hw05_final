from django import template
# добавляем фильтр
register = template.Library()


@register.filter
def addclass(field, css):
    return field.as_widget(attrs={'class': css})
