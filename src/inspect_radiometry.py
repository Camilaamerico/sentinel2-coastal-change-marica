from pathlib import Path
import xml.etree.ElementTree as ET


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"


def local_name(tag):
    """
    Remove XML namespace from a tag.
    """
    return tag.split("}")[-1]


def inspect_radiometry(safe_dir):
    """
    Inspect Sentinel-2 Level-2A radiometric metadata.
    """

    metadata_path = (
        safe_dir
        / "MTD_MSIL2A.xml"
    )

    if not metadata_path.exists():
        raise FileNotFoundError(
            f"Metadata not found: {metadata_path}"
        )

    tree = ET.parse(
        metadata_path
    )

    root = tree.getroot()

    processing_baseline = None
    quantification_value = None
    offsets = []

    for element in root.iter():

        tag = local_name(
            element.tag
        )

        if tag == "PROCESSING_BASELINE":
            processing_baseline = (
                element.text
            )

        elif tag == "BOA_QUANTIFICATION_VALUE":
            quantification_value = float(
                element.text
            )

        elif tag == "BOA_ADD_OFFSET":
            band_id = element.attrib.get(
                "band_id",
                "unknown",
            )

            offsets.append(
                (
                    band_id,
                    float(element.text),
                )
            )

    print("\n====================================")
    print(f"Product: {safe_dir.name}")
    print(
        f"Processing baseline: "
        f"{processing_baseline}"
    )
    print(
        f"BOA quantification value: "
        f"{quantification_value}"
    )

    print("BOA additive offsets:")

    if offsets:
        for band_id, offset in offsets:
            print(
                f"  Band {band_id}: "
                f"{offset}"
            )
    else:
        print(
            "  No BOA_ADD_OFFSET values found."
        )


def main():

    safe_products = sorted(
        RAW_DATA_DIR.glob("*.SAFE")
    )

    print(
        f"SAFE products found: "
        f"{len(safe_products)}"
    )

    for safe_dir in safe_products:
        inspect_radiometry(
            safe_dir
        )


if __name__ == "__main__":
    main()