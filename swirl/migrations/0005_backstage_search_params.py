# WP04: Search.query_template_json, where the search view parks the Backstage
# query params (TECH_DESIGN_swirl_for_backstage.md section 3.5), plus the
# TantivyIndex entry in SearchProvider.CONNECTOR_CHOICES (section 3.4).
#
# The AlterModelOptions operations Django also proposed for querytransform and
# searchprovider are pre-existing drift on develop and are left out.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('swirl', '0004_searchindexgeneration'),
    ]

    operations = [
        migrations.AddField(
            model_name='search',
            name='query_template_json',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name='searchprovider',
            name='connector',
            field=models.CharField(choices=[('ChatGPT', 'ChatGPT Query String'), ('GenAI', 'Generative AI'), ('RequestsGet', 'HTTP/GET returning JSON'), ('RequestsPost', 'HTTP/POST returning JSON'), ('Elastic', 'Elasticsearch Query String'), ('OpenSearch', 'OpenSearch Query String'), ('QdrantDB', 'QdrantDB'), ('BigQuery', 'Google BigQuery'), ('Sqlite3', 'Sqlite3'), ('M365OutlookMessages', 'M365 Outlook Messages'), ('M365OneDrive', 'M365 One Drive'), ('M365OutlookCalendar', 'M365 Outlook Calendar'), ('M365SharePointSites', 'M365 SharePoint Sites'), ('MicrosoftTeams', 'Microsoft Teams'), ('MongoDB', 'MongoDB'), ('Oracle', 'Oracle'), ('Snowflake', 'Snowflake'), ('PineconeDB', 'PineconeDB'), ('TantivyIndex', 'SWIRL Tantivy Index')], default='RequestsGet', max_length=200),
        ),
    ]
