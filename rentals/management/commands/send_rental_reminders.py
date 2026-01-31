"""
Management command to send scheduled reminders for rental operations
Usage: python manage.py send_rental_reminders
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from rentals.models import RentalOrder
from rentals.notifications import RentalWorkflowNotifications


class Command(BaseCommand):
    help = 'Send scheduled reminders for upcoming pickups and returns'
    
    def handle(self, *args, **options):
        """Execute the command"""
        
        # Get current time
        now = timezone.now()
        
        # 1. Send pickup reminders (24 hours before pickup)
        self.send_pickup_reminders(now)
        
        # 2. Send return reminders (24 hours before return date)
        self.send_return_reminders(now)
        
        self.stdout.write(self.style.SUCCESS('Rental reminders sent successfully'))
    
    def send_pickup_reminders(self, now):
        """Send pickup reminders 24 hours before scheduled pickup"""
        
        # Find orders with pickup scheduled in the next 24-25 hours
        tomorrow = now + timedelta(hours=24)
        tomorrow_end = now + timedelta(hours=25)
        
        orders = RentalOrder.objects.filter(
            pickup_date__gte=tomorrow,
            pickup_date__lte=tomorrow_end,
            status='confirmed'
        )
        
        for order in orders:
            try:
                RentalWorkflowNotifications.notify_customer_pickup_reminder(
                    order,
                    days_until_pickup=1
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Pickup reminder sent for order {order.order_number}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to send pickup reminder for {order.order_number}: {str(e)}'
                    )
                )
    
    def send_return_reminders(self, now):
        """Send return reminders 24 hours before return date"""
        
        # Find orders with return due in the next 24-25 hours
        tomorrow = now + timedelta(hours=24)
        tomorrow_end = now + timedelta(hours=25)
        
        orders = RentalOrder.objects.filter(
            rental_end_date__gte=tomorrow,
            rental_end_date__lte=tomorrow_end,
            status='active'  # Rental is ongoing
        )
        
        for order in orders:
            try:
                RentalWorkflowNotifications.notify_customer_return_reminder(
                    order,
                    days_until_return=1
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Return reminder sent for order {order.order_number}'
                    )
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to send return reminder for {order.order_number}: {str(e)}'
                    )
                )
