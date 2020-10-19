from cobbler import enums, utils
from cobbler.api import CobblerAPI
from cobbler.items.image import Image


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    image = Image(test_api)

    # Arrange
    assert isinstance(image, Image)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    result = image.make_clone()

    # Assert
    assert image != result


def test_arch():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.arch = "x86_64"

    # Assert
    assert image.arch == enums.Archs.X86_64


def test_autoinstall():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.autoinstall = ""

    # Assert
    assert image.autoinstall == ""


def test_file():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.file = ""

    # Assert
    assert image.file == ""


def test_os_version():
    # Arrange
    test_api = CobblerAPI()
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")
    image = Image(test_api)
    image.breed = "suse"

    # Act
    image.os_version = "sles15generic"

    # Assert
    assert image.os_version == "sles15generic"


def test_breed():
    # Arrange
    test_api = CobblerAPI()
    utils.load_signatures("/var/lib/cobbler/distro_signatures.json")
    image = Image(test_api)

    # Act
    image.breed = "suse"

    # Assert
    assert image.breed == "suse"


def test_image_type():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.image_type = enums.ImageTypes.DIRECT

    # Assert
    assert image.image_type == enums.ImageTypes.DIRECT


def test_virt_cpus():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_cpus = 5

    # Assert
    assert image.virt_cpus == 5


def test_network_count():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.network_count = 2

    # Assert
    assert image.network_count == 2


def test_virt_auto_boot():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_auto_boot = False

    # Assert
    assert not image.virt_auto_boot


def test_virt_file_size():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_file_size = 500

    # Assert
    assert image.virt_file_size == 500


def test_virt_disk_driver():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_disk_driver = enums.VirtDiskDrivers.RAW

    # Assert
    assert image.virt_disk_driver == enums.VirtDiskDrivers.RAW


def test_virt_ram():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_ram = 5

    # Assert
    assert image.virt_ram == 5


def test_virt_type():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_type = enums.VirtType.AUTO

    # Assert
    assert image.virt_type == enums.VirtType.AUTO


def test_virt_bridge():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_bridge = "testbridge"

    # Assert
    assert image.virt_bridge == "testbridge"


def test_virt_path():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.virt_path = ""

    # Assert
    assert image.virt_path == ""


def test_menu():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.menu = ""

    # Assert
    assert image.menu == ""


def test_supported_boot_loaders():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act & Assert
    assert image.supported_boot_loaders == []


def test_boot_loaders():
    # Arrange
    test_api = CobblerAPI()
    image = Image(test_api)

    # Act
    image.boot_loaders = ""

    # Assert
    assert image.boot_loaders == []
