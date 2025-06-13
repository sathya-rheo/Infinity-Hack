from math import ceil

def paginate(queryset, page: int = 1, limit: int = 10):
    skip = (page - 1) * limit
    paginated = queryset.skip(skip).limit(limit)
    return paginated, skip


def get_genre_list():
    genre_list = ["Action","Adventure","Animation","Aniplex","BROSTA TV","Carousel Productions","Comedy","Crime","Documentary","Drama","Family","Fantasy","Foreign","GoHands","History","Horror","Mardock Scramble Production Committee","Music","Mystery","Odyssey Media","Pulser Productions",
                  "Rogue State","Romance","Science Fiction","Sentai Filmworks","TV Movie","Telescene Film Group Productions","The Cartel","Thriller","Vision View Entertainment","War","Western"
                ]
    return genre_list