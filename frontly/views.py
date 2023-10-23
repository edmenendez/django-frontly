import json
import nh3

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db.models.fields import DateTimeField
from django.http import HttpResponseForbidden
from django.shortcuts import Http404, get_object_or_404, render
from django.templatetags.static import static
from django.utils.crypto import get_random_string

from . import FRONTLY_CHECK_KILLSWITCH_PERM, FRONTLY_SANITIZE
from .templatetags.frontly import set_value

User = get_user_model()


def frontly_editor(request):
    """ Edit front-end content.
    """
    # Basic check for permission to edit. If you don't have this nevermind!
    if FRONTLY_CHECK_KILLSWITCH_PERM and not request.user.has_perm('frontly.frontly_killswitch'):
        return HttpResponseForbidden('You do not have permission to do this.')

    frontly_editor = request.POST.get('frontlyEditor')  # If this exists, then we need to save()
    fe_field = request.POST.get('fe_field').split('.')
    fe_key = request.POST.get('fe_key', 'id')  # optional
    fe_id = request.POST.get('fe_id')
    fe_field_id = f'fc{request.POST.get("fe_field")}-{fe_id}'
    content = request.POST.get('content')  # This is the content that we want edited (triggered by dblClick)
    value = request.POST.get('value')  # This is the edited content if coming from editor
    default = request.POST.get('default', '')
    widget = request.POST.get('widget', 'input')
    kwargs = json.loads(request.POST.get('kwargs', '{}'))
    action = request.POST.get('action')

    if FRONTLY_SANITIZE and value:
        value = nh3.clean(value)

    app_label, model_name, *field_name = fe_field

    # Split the field in case we are also looking for a key in a JSONField
    field_name, *dict_keys = (field_name[0], None) if len(field_name) == 1 else field_name

    model_class = apps.get_model(app_label, model_name)
    model_instance = get_object_or_404(model_class, **{fe_key: fe_id})

    if not model_instance.frontly_permission_check(request.user):
        raise Http404('Not found.')

    context = {
        'fe_field': request.POST.get('fe_field'),
        'fe_id': request.POST.get('fe_id'),
        'fe_field_id': fe_field_id,
        'fe_var': f'F{get_random_string(8)}',
        'content': content,
        'model_instance': model_instance,
        'field_name': field_name,
        'help_text': model_instance._meta.get_field(field_name).help_text,
        'default': default,
        'widget': widget,
        'kwargs': kwargs,
    }

    model_field = getattr(model_instance, field_name)
    if widget == 'img':
        context['content'] = model_field.url if model_field else None

    if not frontly_editor:
        # This means we need to load the editor
        context['is_editing'] = True
        # Remove the class when editing to remove editable highlighting
        kwargs['class'] = kwargs.get('class', '').replace('editable', '')
        return render(request, f'frontly/editor_{widget}.html', context)

    # We made it this far, it's OK to update.
    if widget == 'img':
        uploaded_file = request.FILES.get('image')
        if uploaded_file and action == 'saveBtn':
             model_field.save(uploaded_file.name, uploaded_file)
             context['content'] = model_field
        elif action == 'clearBtn':
             setattr(model_instance, field_name, None)
             context['content'] = None
    else:
        # If the field is a dictionary like object, set the key
        if dict_keys and dict_keys[0] != None:
            model_field = set_value(model_field, dict_keys, value)
            setattr(model_instance, field_name, model_field)
        else:
            clean_function = getattr(model_instance, f'frontly_{field_name}_clean', None)
            if clean_function:
                value = clean_function(value)
            setattr(model_instance, field_name, value)
        context['content'] = value

    # TODO: maybe provide a model_instance.frontly_update_fields() callback to allow override?

    if widget != 'img' or (widget == 'img' and action != 'cancelBtn'):
        # Prepare for save(). Add the auto_now fields to the update.
        update_fields = [field.name for field in model_instance._meta.fields if isinstance(
            field, DateTimeField) and field.auto_now]
        update_fields.append(field_name)
        model_instance.save(update_fields=update_fields)

    return render(request, f'frontly/editor_{widget}.html', context)
