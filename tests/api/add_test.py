from pathlib import Path

from cobbler.items.image import Image


def test_image_add(cobbler_api):
    # Arrange
    test_image = Image(cobbler_api)
    test_image.name = "test_cobbler_api_add_image"
    expected_result = Path(
        "/var/lib/cobbler/collections/images/test_cobbler_api_add_image.json"
    )

    # Act
    cobbler_api.add_image(test_image)

    # Assert
    assert expected_result.exists()
