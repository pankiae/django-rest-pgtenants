# django_rest_pgtenants/management/commands/run_tenant_command.py

import argparse
from typing import Any
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from django_rest_pgtenants.schema_manager import tenant_context

class Command(BaseCommand):
    """
    Django management command to execute another Django management command
    within the context of a specific tenant's database schema.
    """
    help = 'Run a standard Django management command within the context of a specific tenant schema.'

    def add_arguments(self, parser: CommandParser) -> None:
        """
        Define the arguments for the command.
        
        Args:
            parser (CommandParser): The argument parser instance.
        """
        parser.add_argument(
            '--schema',
            type=str,
            required=True,
            help='The target tenant database schema name to run the command under.'
        )
        parser.add_argument(
            'command_name',
            type=str,
            help='The name of the management command to execute (e.g. createsuperuser, shell).'
        )
        parser.add_argument(
            'command_args',
            nargs=argparse.REMAINDER,
            help='Optional arguments and flags passed to the executed command.'
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """
        Execute the target command under the specified tenant schema context.
        
        Args:
            *args (Any): Positional arguments.
            **options (Any): Keyword options.
        """
        schema: str = options['schema']
        command_name: str = options['command_name']
        command_args: list = options['command_args']

        self.stdout.write(self.style.WARNING(
            f"Running command '{command_name}' (args: {command_args}) in schema '{schema}' context..."
        ))

        try:
            with tenant_context(schema):
                call_command(command_name, *command_args)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully completed command '{command_name}' in schema '{schema}' context."
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"Command '{command_name}' failed in schema '{schema}' context: {e}"
            ))
            raise e
