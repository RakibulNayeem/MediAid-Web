# Generated by Django 3.2.9 on 2021-12-20 13:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medi', '0016_alter_blooddonor_blood_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='doctors',
            name='speciality',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.speciality'),
        ),
        migrations.AlterField(
            model_name='doctors',
            name='zilla',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.zilla'),
        ),
    ]