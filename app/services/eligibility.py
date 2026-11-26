from app.models import Category
from app.services.category_structure import GRADES, grade_range


def category_mismatch(athlete, category: Category) -> str | None:
    """`athlete` es cualquier objeto con gender, weight_kg, grade y birth_date (un Athlete o los valores propuestos)."""
    if athlete.gender != category.gender:
        return "El género del atleta no coincide con el de la categoría"
    if category.min_weight is not None and athlete.weight_kg < category.min_weight:
        return "El peso del atleta es menor al mínimo de la categoría"
    if category.max_weight is not None and athlete.weight_kg > category.max_weight:
        return "El peso del atleta es mayor al máximo de la categoría"

    # Edad por año de nacimiento (Art. 4 WT).
    age = category.tournament.date.year - athlete.birth_date.year
    if age < category.min_age or (category.max_age is not None and age > category.max_age):
        ages = f"{category.min_age} a {category.max_age} años" if category.max_age is not None else f"{category.min_age} años o más"
        return f"La edad del atleta ({age}) no corresponde a la categoría ({category.age_label}: {ages})"

    if category.grade_group is not None:
        groups = category.tournament.grade_groups
        first, last = grade_range(groups, groups.index(category.grade_group))
        if not GRADES.index(first) <= GRADES.index(athlete.grade) <= GRADES.index(last):
            return f"El grado del atleta no corresponde al grupo «{category.grade_group.name}» de la categoría"
    return None
