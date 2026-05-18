import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swirl', '0002_alter_result_query_string_to_provider_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AIProvider',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('shared', models.BooleanField(default=True)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_updated', models.DateTimeField(auto_now=True)),
                ('active', models.BooleanField(default=True)),
                ('api_key', models.CharField(blank=True, default=str, max_length=512)),
                ('model', models.CharField(blank=True, default=str, max_length=255)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('tags', models.JSONField(default=list)),
                ('defaults', models.JSONField(default=list)),
                ('prompt_overrides', models.JSONField(blank=True, default=dict)),
                ('owner', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'AIProvider',
                'verbose_name_plural': 'AIProviders',
                'ordering': ['-date_updated'],
            },
        ),
    ]
