from app.models import Category, Gender


def category_mismatch(gender: Gender, weight_kg: float, category: Category) -> str | None:
    if gender != category.gender:
        return "El género del atleta no coincide con el de la categoría"
    if category.min_weight is not None and weight_kg < category.min_weight:
        return "El peso del atleta es menor al mínimo de la categoría"
    if category.max_weight is not None and weight_kg > category.max_weight:
        return "El peso del atleta es mayor al máximo de la categoría"
    return None
