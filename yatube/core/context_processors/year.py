from datetime import datetime


def year(request):
    # Переменная с текущим годом.
    dt = datetime.now().year
    return {
        'year': dt
    }
