# Generated by Django 3.2.9 on 2021-12-19 13:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medi', '0015_alter_blooddonor_zilla'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blooddonor',
            name='blood_group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.bloodgroup'),
        ),
    ]
