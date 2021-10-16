from django.db.models import DecimalField, IntegerField, Subquery


class SQCount(Subquery):
    template = "(SELECT count(*) FROM (%(subquery)s) _count)"
    output_field = IntegerField()


class SQSum(Subquery):
    """Refs. (https://stackoverflow.com/a/58001368)"""

    template = "(SELECT SUM(%(sum_field)s) FROM (%(subquery)s) _sum)"
    output_field = DecimalField()

    def __init__(self, queryset, output_field=None, *, sum_field="", **extra):
        extra["sum_field"] = sum_field
        super().__init__(queryset, output_field, **extra)


class SQAvg(Subquery):
    template = "(SELECT AVG(%(avg_field)s) FROM (%(subquery)s) _avg)"
    output_field = DecimalField()

    def __init__(self, queryset, output_field=None, *, avg_field="", **extra):
        extra["avg_field"] = avg_field
        super().__init__(queryset, output_field, **extra)
