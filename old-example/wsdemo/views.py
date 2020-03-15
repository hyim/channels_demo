from django.template import loader
from django.http import HttpResponse


def index(request):
    context = dict()
    template = loader.get_template('index.html')
    return HttpResponse(template.render(context, request))
