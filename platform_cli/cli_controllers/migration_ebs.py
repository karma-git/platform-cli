from platform_cli.cli_tools.migration_ebs.factories.argparse_configuration import ArgparseConfigMigrationEbsFactory
from platform_cli.cli_tools.migration_ebs.factories.migration_ebs import MigrationEbsFactory
from platform_cli.cli_tools.migration_ebs.services.argparser import get_args


def migration_ebs() -> None:
    args = get_args()
    configuration = ArgparseConfigMigrationEbsFactory(args).create()

    migration = MigrationEbsFactory(configuration).create()
    migration.migrate()


if __name__ == "__main__":
    migration_ebs()
