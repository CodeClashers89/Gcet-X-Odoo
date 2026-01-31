from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, Count, Avg, Q, F, Case, When, Value, DecimalField
from django.db.models.functions import TruncDate, ExtractMonth, ExtractYear
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json


@login_required(login_url='login')
def dashboard(request):
    """
    Role-based dashboard landing page.
    Business Logic:
    - Customers: Browse products, view orders, manage rentals
    - Vendors: Manage inventory, view earnings, process orders
    - Admins: System configuration, approvals, analytics
    """
    user = request.user
    context = {'user': user}
    
    if user.role == 'customer':
        return render(request, 'dashboards/customer_dashboard.html', context)
    elif user.role == 'vendor':
        return render(request, 'dashboards/vendor_dashboard.html', context)
    elif user.role == 'admin':
        return render(request, 'dashboards/admin_dashboard.html', context)
    
    # Fallback
    return render(request, 'dashboards/dashboard.html', context)


# =====================================================================
# ANALYTICS VIEWS (Phase 9)
# =====================================================================

@login_required(login_url='login')
@require_http_methods(["GET"])
def analytics_dashboard(request):
    """
    Main analytics dashboard with KPI cards and quick statistics.
    
    Business Flow:
    - Admin/vendor views key metrics at a glance
    - Quick access to detailed analytics
    - Period-based filtering (today, this week, this month, this year)
    
    RBAC: Admin sees all, vendor sees their own
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view analytics")
    
    from rentals.models import Quotation, RentalOrder, ApprovalRequest
    from billing.models import Invoice, Payment
    
    # Get date range
    period = request.GET.get('period', 'month')
    today = timezone.now().date()
    
    if period == 'today':
        start_date = today
    elif period == 'week':
        start_date = today - timedelta(days=today.weekday())
    elif period == 'month':
        start_date = today.replace(day=1)
    elif period == 'year':
        start_date = today.replace(month=1, day=1)
    else:
        start_date = today.replace(day=1)
    
    end_date = today + timedelta(days=1)
    
    # Filter based on role
    if request.user.role == 'vendor':
        quotations = Quotation.objects.filter(
            quotation_lines__product__vendor=request.user
        ).distinct().filter(created_at__gte=start_date, created_at__lt=end_date)
        
        orders = RentalOrder.objects.filter(
            vendor=request.user,
            created_at__gte=start_date,
            created_at__lt=end_date
        )
    else:
        quotations = Quotation.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        orders = RentalOrder.objects.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
    
    # Calculate KPIs
    total_quotations = quotations.count()
    total_orders = orders.count()
    pending_approvals = ApprovalRequest.objects.filter(
        status='pending',
        created_at__gte=start_date,
        created_at__lt=end_date
    ).count()
    
    total_revenue = orders.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    
    confirmed_orders = orders.filter(status__in=['confirmed', 'in_progress', 'completed']).count()
    conversion_rate = (confirmed_orders / total_quotations * 100) if total_quotations > 0 else 0
    
    # Late orders
    from rentals.models import Return
    late_returns = Return.objects.filter(
        created_at__gte=start_date,
        created_at__lt=end_date,
        is_late_return=True
    ).count()
    
    # Payment status
    pending_payments = Invoice.objects.filter(
        status__in=['draft', 'sent', 'partial'],
        created_at__gte=start_date,
        created_at__lt=end_date
    ).aggregate(Sum('balance_due'))['balance_due__sum'] or Decimal('0.00')
    
    context = {
        'period': period,
        'total_quotations': total_quotations,
        'total_orders': total_orders,
        'confirmed_orders': confirmed_orders,
        'conversion_rate': round(conversion_rate, 2),
        'pending_approvals': pending_approvals,
        'total_revenue': total_revenue,
        'late_returns': late_returns,
        'pending_payments': pending_payments,
        'start_date': start_date,
        'end_date': today,
    }
    
    return render(request, 'dashboards/analytics_dashboard.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def quotation_analytics(request):
    """
    Detailed quotation analytics with trends and status breakdown.
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view analytics")
    
    from rentals.models import Quotation
    
    # Get date range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    # Filter by role
    if request.user.role == 'vendor':
        quotations = Quotation.objects.filter(
            quotation_lines__product__vendor=request.user
        ).distinct().filter(created_at__date__gte=start_date)
    else:
        quotations = Quotation.objects.filter(created_at__date__gte=start_date)
    
    # Status breakdown
    status_stats = quotations.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    ).order_by('status')
    
    # Trend data (daily)
    trend_data = quotations.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    ).order_by('date')
    
    # Calculate metrics
    total_quotations = quotations.count()
    total_amount = quotations.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    avg_amount = quotations.aggregate(Avg('total'))['total__avg'] or Decimal('0.00')
    
    confirmed = quotations.filter(status='confirmed').count()
    confirmation_rate = (confirmed / total_quotations * 100) if total_quotations > 0 else 0
    
    context = {
        'total_quotations': total_quotations,
        'total_amount': total_amount,
        'avg_amount': round(avg_amount, 2),
        'confirmation_rate': round(confirmation_rate, 2),
        'status_stats': list(status_stats),
        'trend_data': list(trend_data),
        'days': days,
        'chart_labels': [str(item['date']) for item in trend_data],
        'chart_data': [int(item['count']) for item in trend_data],
    }
    
    return render(request, 'dashboards/quotation_analytics.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def order_analytics(request):
    """
    Detailed order analytics with fulfillment tracking.
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view analytics")
    
    from rentals.models import RentalOrder
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    if request.user.role == 'vendor':
        orders = RentalOrder.objects.filter(
            vendor=request.user,
            created_at__date__gte=start_date
        )
    else:
        orders = RentalOrder.objects.filter(created_at__date__gte=start_date)
    
    # Status breakdown
    status_stats = orders.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    ).order_by('status')
    
    # Trend data
    trend_data = orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        total_amount=Sum('total')
    ).order_by('date')
    
    # Metrics
    total_orders = orders.count()
    total_amount = orders.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    completed = orders.filter(status='completed').count()
    completion_rate = (completed / total_orders * 100) if total_orders > 0 else 0
    
    context = {
        'total_orders': total_orders,
        'total_amount': total_amount,
        'completion_rate': round(completion_rate, 2),
        'status_stats': list(status_stats),
        'trend_data': list(trend_data),
        'days': days,
        'chart_labels': [str(item['date']) for item in trend_data],
        'chart_data': [int(item['count']) for item in trend_data],
    }
    
    return render(request, 'dashboards/order_analytics.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def approval_analytics(request):
    """
    Approval workflow analytics and statistics.
    """
    if request.user.role != 'admin':
        return HttpResponseForbidden("You don't have permission to view approval analytics")
    
    from rentals.models import ApprovalRequest
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    approvals = ApprovalRequest.objects.filter(created_at__date__gte=start_date)
    
    # Status breakdown
    status_stats = approvals.values('status').annotate(
        count=Count('id'),
        total_amount=Sum('approval_amount')
    ).order_by('status')
    
    # Type breakdown
    type_stats = approvals.values('request_type').annotate(
        count=Count('id'),
        total_amount=Sum('approval_amount')
    ).order_by('request_type')
    
    # By approver
    approver_stats = approvals.filter(approved_by__isnull=False).values(
        'approved_by__first_name', 'approved_by__last_name'
    ).annotate(
        count=Count('id'),
        avg_time=Avg(
            Case(When(approved_at__isnull=False, then=F('approved_at') - F('created_at')))
        )
    ).order_by('-count')
    
    # Metrics
    total_approvals = approvals.count()
    approved_count = approvals.filter(status='approved').count()
    rejected_count = approvals.filter(status='rejected').count()
    pending_count = approvals.filter(status='pending').count()
    
    approval_rate = (approved_count / (approved_count + rejected_count) * 100) if (approved_count + rejected_count) > 0 else 0
    avg_approval_time = approvals.filter(approved_at__isnull=False).aggregate(
        avg=Avg(F('approved_at') - F('created_at'))
    )['avg']
    
    context = {
        'total_approvals': total_approvals,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'pending_count': pending_count,
        'approval_rate': round(approval_rate, 2),
        'avg_approval_time': avg_approval_time,
        'status_stats': list(status_stats),
        'type_stats': list(type_stats),
        'approver_stats': list(approver_stats),
        'days': days,
    }
    
    return render(request, 'dashboards/approval_analytics.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def revenue_analytics(request):
    """
    Revenue and financial analytics dashboard.
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view revenue analytics")
    
    from rentals.models import RentalOrder
    from billing.models import Invoice, Payment
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    if request.user.role == 'vendor':
        orders = RentalOrder.objects.filter(
            vendor=request.user,
            created_at__date__gte=start_date
        )
    else:
        orders = RentalOrder.objects.filter(created_at__date__gte=start_date)
    
    # Revenue metrics
    total_revenue = orders.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    total_discount = orders.aggregate(Sum('discount_amount'))['discount_amount__sum'] or Decimal('0.00')
    total_tax = orders.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
    total_late_fees = orders.aggregate(Sum('late_fee'))['late_fee__sum'] or Decimal('0.00')
    
    # Payment tracking
    total_paid = orders.aggregate(Sum('paid_amount'))['paid_amount__sum'] or Decimal('0.00')
    total_due = orders.aggregate(Sum(F('total') - F('paid_amount')))['total__sum'] or Decimal('0.00')
    
    payment_rate = (total_paid / total_revenue * 100) if total_revenue > 0 else 0
    
    # Daily trend
    daily_revenue = orders.annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        amount=Sum('total')
    ).order_by('date')
    
    context = {
        'total_revenue': total_revenue,
        'total_discount': total_discount,
        'total_tax': total_tax,
        'total_late_fees': total_late_fees,
        'total_paid': total_paid,
        'total_due': total_due,
        'payment_rate': round(payment_rate, 2),
        'daily_revenue': list(daily_revenue),
        'days': days,
        'chart_labels': [str(item['date']) for item in daily_revenue],
        'chart_data': [float(item['amount']) for item in daily_revenue],
    }
    
    return render(request, 'dashboards/revenue_analytics.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def inventory_analytics(request):
    """
    Inventory availability and utilization analytics.
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view inventory analytics")
    
    from catalog.models import Product, ProductVariant
    from rentals.models import Reservation
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    end_date = start_date + timedelta(days=days)
    
    if request.user.role == 'vendor':
        products = Product.objects.filter(vendor=request.user)
    else:
        products = Product.objects.all()
    
    # Total inventory
    total_products = products.count()
    total_variants = ProductVariant.objects.filter(product__in=products).count()
    
    # Utilization - reservations in period
    reserved_items = Reservation.objects.filter(
        product__in=products,
        rental_start_date__date__lte=end_date,
        rental_end_date__date__gte=start_date
    ).count()
    
    # Products with most reservations
    top_products = Reservation.objects.filter(
        product__in=products,
        rental_start_date__date__lte=end_date,
        rental_end_date__date__gte=start_date
    ).values('product__name').annotate(
        reservation_count=Count('id')
    ).order_by('-reservation_count')[:10]
    
    context = {
        'total_products': total_products,
        'total_variants': total_variants,
        'reserved_items': reserved_items,
        'top_products': list(top_products),
        'days': days,
    }
    
    return render(request, 'dashboards/inventory_analytics.html', context)


@login_required(login_url='login')
@require_http_methods(["GET"])
def late_returns_analytics(request):
    """
    Late return tracking and penalty analytics.
    """
    if request.user.role not in ['admin', 'vendor']:
        return HttpResponseForbidden("You don't have permission to view late returns analytics")
    
    from rentals.models import Return
    
    days = int(request.GET.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    if request.user.role == 'vendor':
        returns = Return.objects.filter(
            rental_order__vendor=request.user,
            created_at__date__gte=start_date
        )
    else:
        returns = Return.objects.filter(created_at__date__gte=start_date)
    
    # Late return stats
    total_returns = returns.count()
    late_returns = returns.filter(is_late_return=True).count()
    late_rate = (late_returns / total_returns * 100) if total_returns > 0 else 0
    
    # Fee tracking
    total_late_fees = returns.aggregate(Sum('late_fee_charged'))['late_fee_charged__sum'] or Decimal('0.00')
    avg_late_days = returns.filter(is_late_return=True).aggregate(Avg('late_days'))['late_days__avg'] or 0
    
    # Daily trend
    daily_late = returns.filter(is_late_return=True).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        count=Count('id'),
        total_fees=Sum('late_fee_charged')
    ).order_by('date')
    
    context = {
        'total_returns': total_returns,
        'late_returns': late_returns,
        'late_rate': round(late_rate, 2),
        'total_late_fees': total_late_fees,
        'avg_late_days': round(avg_late_days, 1),
        'daily_late': list(daily_late),
        'days': days,
    }
    
    return render(request, 'dashboards/late_returns_analytics.html', context)

