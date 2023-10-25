# Generated by Django 3.2.9 on 2021-12-20 13:33

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('medi', '0017_auto_20211220_1906'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ambulance',
            name='type',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.ambulancetype'),
        ),
        migrations.AlterField(
            model_name='ambulance',
            name='zilla',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.zilla'),
        ),
        migrations.AlterField(
            model_name='bloodbank',
            name='zilla',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.zilla'),
        ),
        migrations.AlterField(
            model_name='hospital',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.category'),
        ),
        migrations.AlterField(
            model_name='hospital',
            name='zilla',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='medi.zilla'),
        ),
    ]
