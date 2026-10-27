"""Add SearchProvider.config (WP05).

Free-form provider configuration keyed by namespace; SWIRL's own keys live
under config['swirl']. Today that is config['swirl']['scope_unrestricted'],
the bypass for the scope rule in swirl/scope.py.

The unrelated AlterModelOptions operations that makemigrations also offers for
this app are pre-existing drift and are deliberately left out of this
migration.

Renumbered from 0004 to 0006 at integration time: lane A's
0004_searchindexgeneration and 0005_backstage_search_params already occupy
those numbers, so this one depends on 0005 and the chain stays linear.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swirl', '0005_backstage_search_params'),
    ]

    operations = [
        migrations.AddField(
            model_name='searchprovider',
            name='config',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
