from django.db import migrations, models


def backfill_payment_receipts(apps, schema_editor):
    Payment = apps.get_model("sales", "Payment")
    table = schema_editor.quote_name(Payment._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"SELECT id FROM {table} "
            "WHERE receipt_number IS NULL OR receipt_number = '' "
            "ORDER BY id"
        )
        rows = cursor.fetchall()
        for (pk,) in rows:
            cursor.execute(
                f"UPDATE {table} SET receipt_number = %s WHERE id = %s",
                [f"RCT-{pk:06d}", pk],
            )


def clear_payment_receipts(apps, schema_editor):
    Payment = apps.get_model("sales", "Payment")
    table = schema_editor.quote_name(Payment._meta.db_table)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f"UPDATE {table} SET receipt_number = NULL")


class Migration(migrations.Migration):

    dependencies = [
        ("sales", "0004_financials"),
    ]

    operations = [
        migrations.AddField(
            model_name="payment",
            name="receipt_number",
            field=models.CharField(
                blank=True, max_length=20, null=True, unique=True, verbose_name="Receipt No."
            ),
        ),
        migrations.RunPython(backfill_payment_receipts, clear_payment_receipts),
        migrations.AlterField(
            model_name="payment",
            name="receipt_number",
            field=models.CharField(
                blank=True, max_length=20, unique=True, verbose_name="Receipt No."
            ),
        ),
        migrations.RemoveField(
            model_name="invoice",
            name="attachment",
        ),
    ]
