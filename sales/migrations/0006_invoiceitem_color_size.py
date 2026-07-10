from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0005_payment_receipts"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="color",
            field=models.CharField(blank=True, max_length=16, null=True, verbose_name="Color"),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="size",
            field=models.CharField(blank=True, max_length=120, null=True, verbose_name="Size / Spec"),
        ),
    ]
