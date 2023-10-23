import copy
from django import template
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def fr_input(user, instance, field, default='', **kwargs):
    """Display an HTMX compatible control."""
    return fr_abstract(user, instance, field, default, 'input', **kwargs)


@register.simple_tag
def fr_textarea(user, instance, field, default='', **kwargs):
    """Display an HTMX compatible control."""
    return fr_abstract(user, instance, field, default, 'textarea', **kwargs)


@register.simple_tag
def fr_img(user, instance, field, default='', **kwargs):
    """Display an HTMX compatible control."""
    return fr_abstract(user, instance, field, default, 'img', **kwargs)


@register.simple_tag
def fr_timepicker(user, instance, field, default='', **kwargs):
    """Display an HTMX compatible control."""
    return fr_abstract(user, instance, field, default, 'timepicker', **kwargs)


def fr_abstract(user, instance, field, default, widget, **kwargs):
    """ Abstraction for the diffrent widget types
    """
    app_name = instance._meta.app_label
    model_name = instance._meta.model_name

    # Append the editable class
    kwargs.setdefault('class', '')
    kwargs['class'] = ' '.join(kwargs['class'].split(' ') + ['editable']).strip()

    if '.' in field:
        field_name, *keys = field.split('.')
        model_field = getattr(instance, field_name)
        content = find_value(model_field, keys)
        help_text = ''  # TODO: would be nice
    else:
        content = getattr(instance, field)
        help_text = instance._meta.get_field(field).help_text

    if not user.has_perm('frontly.frontly_killswitch'):
        # Short circuit it here because there's no editing capability
        if widget == 'img':
            other_args = ''
            for kwarg, value in kwargs.items():
                other_args += f' {kwarg}="{value}" '
            url = content and content.url or default
            return mark_safe(f'<img src="{url}" {other_args}>')
        return mark_safe(content or default)

    context = {
        'fe_field': f'{app_name}.{model_name}.{field}',
        'fe_id': instance.pk,
        'fe_var': f'F{get_random_string(8)}',  # Useful for variable names in JS
        'content': content,
        'default': default,
        'help_text': help_text,
        'kwargs': kwargs,
    }
    context['fe_field_id'] = f'fc{context["fe_field"]}-{context["fe_id"]}'

    return render_to_string(f'frontly/editor_{widget}.html', context)


def find_value(my_dict, keys):
    """ Given nested dictionaries, find the values by diving through the keys.
    """
    content = my_dict
    for key in keys:
        content = content.get(key, '')
    return content


def set_value(my_dict, keys, value):
    """ Set's the value deep in a dictionary.
    >>>> set_value({}, ['test', 'something', 'new'], 123)
    {'test': {'something': {'new': 123}}}
    """
    _my_dict = copy.deepcopy(my_dict)
    content = _my_dict
    for key in keys:
        content.setdefault(key, dict())
        if key == keys[-1]:
            content[key] = value
        else:
            content = content.get(key)
    return _my_dict


@register.tag(name='frontly_can_edit')
def do_frontly_can_edit(parser, token):
    """ Anything between {% frontly_can_edit user_profile %}this{% frontly_can_edit_end %}
    Will only show if user_profile.frontly_permission_check(request.user) returns True.
    """
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, instance = token.split_contents()
    except ValueError:
        msg = '%r tag requires a single argument' % token.split_contents()[0]
        raise template.TemplateSyntaxError(msg)

    nodelist = parser.parse(('frontly_can_edit_end',))
    parser.delete_first_token()
    return FrontlyCanEditNode(nodelist, instance)


class FrontlyCanEditNode(template.Node):
    def __init__(self, nodelist, instance):
        self.nodelist = nodelist
        self.instance = template.Variable(instance)
        self.request = template.Variable('request')

    def render(self, context):
        instance_value = self.instance.resolve(context)
        request = self.request.resolve(context)

        if instance_value.frontly_permission_check(request.user):
            return self.nodelist.render(context)
        else:
            return ''