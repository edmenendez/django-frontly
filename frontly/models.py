from django.db import models


class FrontlyKillSwitch(models.Model):
    """ Just a proxy model to handle the permission.
    """
    class Meta:
        managed = False
        permissions = (
            ('frontly_killswitch', 'Can activate frontly kill switch'),
        )
