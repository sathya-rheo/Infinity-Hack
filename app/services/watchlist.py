
def paginate_list(items, page, limit):
    start = (page - 1) * limit
    end = start + limit
    return items[start:end]
