# Generated by Django 4.2.16 on 2025-05-04 16:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comptabilite', '0001_initial'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='ecriturecomptable',
            name='tiers_exclusif',
        ),
    ]
