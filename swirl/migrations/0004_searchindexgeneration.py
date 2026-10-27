# WP02: SearchIndexGeneration, the bookkeeping table for the Backstage ingest
# API (TECH_DESIGN_swirl_for_backstage.md section 3.2).
#
# The AlterModelOptions operations Django also proposed for querytransform and
# searchprovider are pre-existing drift on develop, unrelated to this work
# package, and are deliberately left out.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swirl', '0003_add_aiprovider'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SearchIndexGeneration',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('type', models.CharField(max_length=64)),
                ('generation', models.CharField(max_length=32)),
                ('state', models.CharField(choices=[('open', 'Open'), ('live', 'Live'), ('aborted', 'Aborted'), ('retired', 'Retired')], default='open', max_length=16)),
                ('doc_count', models.IntegerField(default=0)),
                ('bytes', models.BigIntegerField(default=0)),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('finalized_at', models.DateTimeField(blank=True, null=True)),
                ('started_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'SearchIndexGeneration',
                'verbose_name_plural': 'SearchIndexGenerations',
                'ordering': ['-started_at'],
                'unique_together': {('type', 'generation')},
            },
        ),
    ]
