# Generated by Django 5.1.6 on 2025-02-09 05:42

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testfarmer', '0002_rating'),
    ]

    operations = [
        migrations.CreateModel(
            name='Reply',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reply_text', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('farmer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='testfarmer.farmerprofile')),
                ('rating', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='replies', to='testfarmer.rating')),
            ],
        ),
    ]
