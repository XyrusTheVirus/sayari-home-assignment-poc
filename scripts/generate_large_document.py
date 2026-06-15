"""Generate deterministic large sample document content."""

from pathlib import Path

PEOPLE = ["Ava Morgan", "Noah Patel", "Mia Chen", "Liam Brooks", "Sophia Rivera"]
COMPANIES = ["Acme Corp", "Northstar Technologies", "Helios Bank", "Cedar Systems", "Atlas Group"]
STREETS = ["100 Market Street", "245 Innovation Ave", "18 Cedar Road", "700 Mission Blvd", "42 Lake Drive"]
CITIES = ["New York", "San Francisco", "Chicago", "Boston", "Austin"]


def build_document(records: int = 35) -> str:
    """Build a deterministic business-record style document with many entities."""

    paragraphs: list[str] = []
    for index in range(records):
        person = PEOPLE[index % len(PEOPLE)]
        company = COMPANIES[index % len(COMPANIES)]
        street = STREETS[index % len(STREETS)]
        city = CITIES[index % len(CITIES)]
        month = (index % 12) + 1
        day = (index % 27) + 1
        paragraphs.append(
            f"On 2026-{month:02d}-{day:02d}, {person} confirmed that {company} opened a review office "
            f"at {street} in {city}. The record references Project Falcon {index}, which remains an "
            f"internal label rather than a named entity. {company} expects a follow-up meeting with {person} "
            f"on June {day}, 2026.\n"
        )
        if index == records // 2:
            paragraphs.append("\f")
    return "\n".join(paragraphs)


def main() -> None:
    """Write the generated document to test_documents/large.txt."""

    output = Path(__file__).resolve().parents[1] / "test_documents" / "large.txt"
    output.write_text(build_document(), encoding="utf-8")


if __name__ == "__main__":
    main()
