# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Cobbler?

Cobbler is a Linux installation server that automates network installation environments. It manages PXE booting,
autoinstallation (kickstart/preseed/autoyast), DHCP, DNS, TFTP, and configuration management orchestration for rapid
deployment of Linux systems.

## Development Commands

All development has to be done inside the Docker Compose Stack due to the dependency on the managed daemons that aren't
available locally.

### Building
```bash
# Build the package
make build

# Build RPMs
make rpms

# Build DEBs  
make debs

# Clean build artifacts
make clean
```

### Testing
```bash
# Run unit tests (default - excludes integration tests)
pytest

# Run unit tests with coverage
pytest --cov=./cobbler

# Run integration tests (marked with @pytest.mark.integration)
pytest -m integration

# Run system tests
make system-test

# Run specific distribution tests in Docker
make test-rocky9
make test-fedora41
make test-debian12
```

### Code Quality
```bash
# Format code with black
make qa

# Run pre-commit hooks
pre-commit run --all-files
```

### Installation
```bash
# Install locally for development
make install DESTDIR=/path/to/install
```

## Architecture

### Core Object Hierarchy

Cobbler uses an object-oriented design with inheritance:

```
BaseItem (cobbler/items/abstract/base_item.py)
├── InheritableItem (cobbler/items/abstract/inheritable_item.py)
│   ├── BootableItem (cobbler/items/abstract/bootable_item.py)
│   │   ├── Distro (cobbler/items/distro.py)
│   │   ├── Profile (cobbler/items/profile.py)
│   │   ├── System (cobbler/items/system.py)
│   │   └── Image (cobbler/items/image.py)
│   ├── Repo (cobbler/items/repo.py)
│   └── Menu (cobbler/items/menu.py)
├── NetworkInterface (cobbler/items/network_interface.py)
└── Template (cobbler/items/template.py)
```

**Key inheritance pattern**: Profiles inherit from Distros, Systems inherit from Profiles. This creates a hierarchy: Distro → Profile → System, where lower-level objects inherit properties from their parents unless explicitly overridden.

### Collections Layer

Each item type has a corresponding collection class in `cobbler/cobbler_collections/`:
- `collection.py`: Abstract base collection with CRUD operations
- `distros.py`, `profiles.py`, `systems.py`, etc.: Concrete collections

Collections are managed by `CollectionManager` (`manager.py`) which coordinates all collections.

### API Layers

1. **Python API** (`cobbler/api.py`): Main API for internal use and external Python clients
   - Provides methods like `new_distro()`, `add_distro()`, `find_distro()`, etc.
   - Used by CLI tools and the XML-RPC API

2. **XML-RPC API** (`cobbler/remote.py`): Remote API for network clients
   - Wraps the Python API for remote access
   - Used by web UI and remote management tools

### Module System (Plugin Architecture)

Cobbler uses a plugin system in `cobbler/modules/`:

- **authentication/**: Authentication backends (configfile, ldap, pam, etc.)
- **authorization/**: Authorization backends (allowall, ownership)
- **installation/**: Pre/post installation hooks (pre_log, post_power, post_puppet, etc.)
- **managers/**: Service managers for DHCP/DNS/TFTP
  - `bind.py`: BIND DNS manager
  - `dnsmasq.py`: dnsmasq DHCP/DNS manager
  - `isc.py`: ISC DHCP manager
  - `in_tftpd.py`: in.tftpd manager
  - `import_signatures.py`: OS detection signatures
- **serializers/**: Storage backends (file, mongodb)

Modules are dynamically loaded by `module_loader.py`.

### Settings and Configuration

- `cobbler/settings/`: Settings management with schema validation
- `cobbler/settings/migrations/`: Automatic settings migrations between versions
- Settings are validated using the `schema` library (`cobbler/validate.py`)

### Service Generation

- `cobbler/tftpgen.py`: Generates TFTP configuration and PXE menus
- `cobbler/services.py`: Manages DHCP/DNS service configuration
- `cobbler/yumgen.py`: Generates YUM repository configurations
- `cobbler/configgen.py`: Template-based configuration generation

## Testing Structure

- `tests/`: Unit tests mirroring the `cobbler/` structure
  - Mark integration tests with `@pytest.mark.integration`
  - Use fixtures from `conftest.py`
- `system-tests/`: System-level integration tests
- `tests/test_data/`: Test fixtures and sample data

## Working with Items

When modifying items (Distro, Profile, System, etc.):

1. **Item definitions**: Start in `cobbler/items/` (e.g., `distro.py`)
2. **Collection management**: Update corresponding collection in `cobbler/cobbler_collections/`
3. **API exposure**: Ensure CRUD methods exist in `cobbler/api.py`
4. **XML-RPC exposure**: Add remote methods in `cobbler/remote.py` if needed
5. **Validation**: Add property validation in the item's setter methods
6. **Tests**: Add tests in `tests/items/` or `tests/cobbler_collections/`

## Property System

Modern Cobbler uses properties (getters/setters) instead of direct attributes:
- Inherited properties use the `@InheritableProperty` decorator
- Lazy-loaded properties use the `@LazyProperty` decorator
- Properties should validate input and handle type conversion
- Use `enums.py` for enumerated values

## Inheritance and Resolution

Items support inheritance via the `parent` relationship:
- Profiles inherit from Distros
- Systems inherit from Profiles
- Use `VALUE_INHERITED` (from `enums.py`) to explicitly inherit a value
- Resolution methods walk the inheritance chain to find actual values

## File Locations When Running

When Cobbler is installed, key directories:
- `/var/lib/cobbler/`: Data storage (when using file serializer)
- `/etc/cobbler/`: Configuration files
- `/var/www/cobbler/`: Web-accessible files
- `/srv/tftp/`: TFTP boot files

## Docker Development

Use Docker Compose for development:

```bash
docker compose -f docker/tests/compose.yml up -d
```

Individual distribution test containers are defined in `docker/rpms/` and `docker/debs/`.