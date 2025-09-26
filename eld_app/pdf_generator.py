"""
PDF Generation for Daily Log Sheets
Generates FMCSA-compliant daily log PDFs
"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect, Line
from reportlab.graphics import renderPDF
from datetime import datetime, timedelta
from decimal import Decimal
import io
import logging

logger = logging.getLogger(__name__)


class DailyLogPDFGenerator:
    """Generate FMCSA-compliant daily log PDFs"""
    
    def __init__(self):
        self.page_width, self.page_height = letter
        self.margin = 0.5 * inch
        self.content_width = self.page_width - (2 * self.margin)
        self.content_height = self.page_height - (2 * self.margin)
        
        # Styles
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='Title',
            parent=self.styles['Heading1'],
            fontSize=16,
            spaceAfter=12,
            alignment=TA_CENTER,
            textColor=colors.blue
        ))
        
        self.styles.add(ParagraphStyle(
            name='Header',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            alignment=TA_LEFT
        ))
        
        self.styles.add(ParagraphStyle(
            name='Small',
            parent=self.styles['Normal'],
            fontSize=8,
            spaceAfter=3,
            alignment=TA_LEFT
        ))
    
    def generate_daily_log_pdf(self, daily_log, duty_statuses=None):
        """Generate PDF for daily log"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin
        )
        
        story = []
        
        # Add header
        story.extend(self._create_header(daily_log))
        story.append(Spacer(1, 0.1 * inch))
        
        # Add driver information
        story.extend(self._create_driver_info(daily_log))
        story.append(Spacer(1, 0.1 * inch))
        
        # Add HOS grid
        story.extend(self._create_hos_grid(daily_log, duty_statuses))
        story.append(Spacer(1, 0.1 * inch))
        
        # Add totals section
        story.extend(self._create_totals_section(daily_log))
        story.append(Spacer(1, 0.1 * inch))
        
        # Add remarks section
        story.extend(self._create_remarks_section(daily_log))
        story.append(Spacer(1, 0.1 * inch))
        
        # Add recap section
        story.extend(self._create_recap_section(daily_log))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_header(self, daily_log):
        """Create PDF header"""
        elements = []
        
        # Title
        elements.append(Paragraph("U.S. DEPARTMENT OF TRANSPORTATION", self.styles['Title']))
        elements.append(Paragraph("DRIVER'S DAILY LOG (ONE CALENDAR DAY – 24 HOURS)", self.styles['Title']))
        
        # Instructions
        instructions = [
            "ORIGINAL – Submit to carrier within 13 days",
            "DUPLICATE – Driver retains possession for eight days"
        ]
        
        for instruction in instructions:
            elements.append(Paragraph(instruction, self.styles['Small']))
        
        return elements
    
    def _create_driver_info(self, daily_log):
        """Create driver information section"""
        elements = []
        
        # Driver info table
        driver_data = [
            ['Date:', f"{daily_log.log_date.strftime('%m %d %Y')}", 'Total Miles Driving Today:', f"{daily_log.total_miles_driven}"],
            ['Truck/Tractor and Trailer Numbers:', f"{daily_log.vehicle_numbers}", '', ''],
            ['Name of Carrier:', f"{daily_log.driver.carrier_name}", '', ''],
            ['Main Office Address:', f"{daily_log.driver.carrier_address}", '', ''],
            ['Driver\'s Signature:', f"{daily_log.driver.user.get_full_name()}", '', ''],
            ['Name of Co-Driver:', '', '', '']
        ]
        
        driver_table = Table(driver_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 1.5*inch])
        driver_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(driver_table)
        elements.append(Spacer(1, 0.1 * inch))
        
        # Certification
        elements.append(Paragraph("I certify that these entries are true and correct", self.styles['Small']))
        
        return elements
    
    def _create_hos_grid(self, daily_log, duty_statuses=None):
        """Create HOS grid with duty status lines"""
        elements = []
        
        # Grid title
        elements.append(Paragraph("The Graph Grid", self.styles['Header']))
        
        # Create grid table
        grid_data = self._create_grid_data(daily_log, duty_statuses)
        
        # Calculate column widths (24 hours = 24 columns)
        hour_width = self.content_width / 25  # 24 hours + 1 for duty status column
        
        grid_table = Table(grid_data, colWidths=[1*inch] + [hour_width] * 24)
        grid_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        
        elements.append(grid_table)
        
        return elements
    
    def _create_grid_data(self, daily_log, duty_statuses=None):
        """Create grid data with duty status lines"""
        # Time headers
        time_headers = ['Midnight', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', 
                       'Noon', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23']
        
        # Duty status rows
        duty_statuses_list = ['Off Duty', 'Sleeper Berth', 'Driving', 'On Duty (Not Driving)']
        
        # Create grid
        grid_data = [[''] + time_headers]
        
        for duty_status in duty_statuses_list:
            row = [duty_status] + [''] * 24
            grid_data.append(row)
        
        # Add duty status lines if provided
        if duty_statuses:
            self._add_duty_status_lines(grid_data, duty_statuses, daily_log.log_date)
        
        return grid_data
    
    def _add_duty_status_lines(self, grid_data, duty_statuses, log_date):
        """Add duty status lines to grid"""
        # Map duty status to row index
        status_to_row = {
            'off_duty': 1,
            'sleeper_berth': 2,
            'driving': 3,
            'on_duty_not_driving': 4
        }
        
        for status in duty_statuses:
            if status.status in status_to_row:
                row_idx = status_to_row[status.status]
                
                # Calculate start and end hour columns
                start_hour = status.start_time.hour
                end_hour = status.end_time.hour if status.end_time else 23
                
                # Mark the time period
                for hour in range(start_hour, end_hour + 1):
                    if 0 <= hour <= 23:
                        col_idx = hour + 1  # +1 for duty status column
                        grid_data[row_idx][col_idx] = '█'  # Solid block character
    
    def _create_totals_section(self, daily_log):
        """Create totals section"""
        elements = []
        
        # Totals table
        totals_data = [
            ['TOTAL HOURS', 'Off Duty', 'Sleeper Berth', 'Driving', 'On Duty (Not Driving)'],
            ['', f"{daily_log.off_duty_hours}", f"{daily_log.sleeper_berth_hours}", 
             f"{daily_log.driving_hours}", f"{daily_log.on_duty_not_driving_hours}"]
        ]
        
        totals_table = Table(totals_data, colWidths=[1*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ]))
        
        elements.append(totals_table)
        
        return elements
    
    def _create_remarks_section(self, daily_log):
        """Create remarks section"""
        elements = []
        
        elements.append(Paragraph("REMARKS", self.styles['Header']))
        
        # Remarks box
        remarks_data = [
            ['Pro or Shipping No.', ''],
            ['', ''],
            ['', ''],
            ['', ''],
            ['', ''],
            ['', ''],
        ]
        
        remarks_table = Table(remarks_data, colWidths=[2*inch, 4*inch])
        remarks_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(remarks_table)
        
        return elements
    
    def _create_recap_section(self, daily_log):
        """Create recap section with HOS calculations"""
        elements = []
        
        elements.append(Paragraph("Recap: Complete at end of day", self.styles['Header']))
        
        # Recap table
        recap_data = [
            ['Enter name of place you reported and where released from work and when and where each change of duty occurred. Use time standard of home terminal.'],
            ['', ''],
            ['', ''],
            ['On duty hours today, Total lines 3 & 4:', f"{daily_log.driving_hours + daily_log.on_duty_not_driving_hours}"],
            ['', ''],
            ['70 Hour / 8 Day Drivers:', ''],
            ['A. Total hours on duty last 7 days including today:', f"{daily_log.total_hours_last_7_days}"],
            ['B. Total hours available tomorrow 70 hr. minus A*:', f"{daily_log.hours_available_tomorrow}"],
            ['C. Total hours on duty last 5 days including today:', f"{daily_log.total_hours_last_5_days}"],
            ['', ''],
            ['60 Hour / 7 Day Drivers:', ''],
            ['A. Total hours on duty last 7 days including today:', f"{daily_log.total_hours_last_7_days}"],
            ['B. Total hours available tomorrow 60 hr. minus A*:', f"{daily_log.hours_available_tomorrow}"],
            ['C. Total hours on duty last 7 days including today:', f"{daily_log.total_hours_last_7_days}"],
            ['', ''],
            ['If you took 34 consecutive hours off duty you have 60/70 hours available', '']
        ]
        
        recap_table = Table(recap_data, colWidths=[4*inch, 2*inch])
        recap_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('SPAN', (0, 0), (1, 0)),  # Span first row
            ('SPAN', (0, 1), (1, 1)),  # Span second row
            ('SPAN', (0, 2), (1, 2)),  # Span third row
            ('SPAN', (0, 4), (1, 4)),  # Span fifth row
            ('SPAN', (0, 5), (1, 5)),  # Span sixth row
            ('SPAN', (0, 9), (1, 9)),  # Span tenth row
            ('SPAN', (0, 10), (1, 10)),  # Span eleventh row
            ('SPAN', (0, 14), (1, 14)),  # Span fifteenth row
            ('SPAN', (0, 15), (1, 15)),  # Span sixteenth row
        ]))
        
        elements.append(recap_table)
        
        return elements


class MultiDayLogPDFGenerator:
    """Generate multi-day log PDFs for longer trips"""
    
    def __init__(self):
        self.single_day_generator = DailyLogPDFGenerator()
    
    def generate_multi_day_pdf(self, trip, daily_logs):
        """Generate PDF for multi-day trip"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )
        
        story = []
        
        # Add trip header
        story.extend(self._create_trip_header(trip))
        story.append(PageBreak())
        
        # Add daily logs
        for daily_log in daily_logs:
            # Get duty statuses for this day
            duty_statuses = self._get_duty_statuses_for_day(daily_log)
            
            # Generate single day log
            single_day_pdf = self.single_day_generator.generate_daily_log_pdf(
                daily_log, duty_statuses
            )
            
            # Add page break between days
            if daily_log != daily_logs[0]:
                story.append(PageBreak())
            
            # Add daily log content
            story.extend(self._create_daily_log_content(daily_log, duty_statuses))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def _create_trip_header(self, trip):
        """Create trip header"""
        elements = []
        
        elements.append(Paragraph("TRIP SUMMARY", self.single_day_generator.styles['Title']))
        elements.append(Paragraph(f"Trip ID: {trip.id}", self.single_day_generator.styles['Header']))
        elements.append(Paragraph(f"Origin: {trip.origin_address}", self.single_day_generator.styles['Header']))
        elements.append(Paragraph(f"Destination: {trip.destination_address}", self.single_day_generator.styles['Header']))
        elements.append(Paragraph(f"Total Distance: {trip.total_distance_miles} miles", self.single_day_generator.styles['Header']))
        elements.append(Paragraph(f"Estimated Duration: {trip.estimated_duration_hours} hours", self.single_day_generator.styles['Header']))
        
        return elements
    
    def _get_duty_statuses_for_day(self, daily_log):
        """Get duty statuses for a specific day"""
        from .models import DutyStatus
        
        start_of_day = datetime.combine(daily_log.log_date, datetime.min.time())
        end_of_day = start_of_day + timedelta(days=1)
        
        return DutyStatus.objects.filter(
            driver=daily_log.driver,
            start_time__gte=start_of_day,
            start_time__lt=end_of_day
        ).order_by('start_time')
    
    def _create_daily_log_content(self, daily_log, duty_statuses):
        """Create daily log content for multi-day PDF"""
        elements = []
        
        # Add date header
        elements.append(Paragraph(f"Day: {daily_log.log_date.strftime('%B %d, %Y')}", 
                                 self.single_day_generator.styles['Header']))
        
        # Add HOS grid
        elements.extend(self.single_day_generator._create_hos_grid(daily_log, duty_statuses))
        
        # Add totals
        elements.extend(self.single_day_generator._create_totals_section(daily_log))
        
        return elements
