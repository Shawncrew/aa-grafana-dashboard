from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aagrafanadashboard", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="CorporationMemberTracking",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("corporation_id", models.IntegerField(db_index=True)),
                ("character_id", models.IntegerField()),
                ("character_name", models.CharField(blank=True, max_length=64)),
                ("logon_date", models.DateTimeField(blank=True, null=True)),
                ("logoff_date", models.DateTimeField(blank=True, null=True)),
                ("ship_type_id", models.IntegerField(blank=True, null=True)),
                ("ship_type_name", models.CharField(blank=True, max_length=64)),
                ("location_id", models.BigIntegerField(blank=True, null=True)),
                ("start_date", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "unique_together": {("corporation_id", "character_id")},
            },
        ),
    ]
