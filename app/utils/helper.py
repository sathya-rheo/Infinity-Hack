from math import ceil

def paginate(queryset, page: int = 1, limit: int = 10):
    skip = (page - 1) * limit
    paginated = queryset.skip(skip).limit(limit)
    return paginated, skip
