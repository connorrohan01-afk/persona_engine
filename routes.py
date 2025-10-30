from flask import render_template, request, jsonify, redirect, url_for, flash
from datetime import datetime, timedelta
from app import app, db
from models import ContentTemplate, GeneratedContent, PlatformConnection, PostAnalytics
from content_generator import get_content_generator
from scheduler import content_scheduler
import json


@app.route('/')
def index():
    """Dashboard with overview statistics"""
    total_content = GeneratedContent.query.count()
    published_content = GeneratedContent.query.filter_by(status='published').count()
    scheduled_content = GeneratedContent.query.filter_by(status='scheduled').count()
    connected_platforms = PlatformConnection.query.filter_by(is_connected=True).count()
    
    recent_content = GeneratedContent.query.order_by(GeneratedContent.created_at.desc()).limit(5).all()
    
    return render_template('index.html', 
                         total_content=total_content,
                         published_content=published_content,
                         scheduled_content=scheduled_content,
                         connected_platforms=connected_platforms,
                         recent_content=recent_content)


@app.route('/generate')
def generate_page():
    """Content generation page"""
    templates = ContentTemplate.query.all()
    platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'blog']
    return render_template('generate.html', templates=templates, platforms=platforms)


@app.route('/api/generate-content', methods=['POST'])
def api_generate_content():
    """API endpoint to generate content"""
    try:
        data = request.get_json()
        
        template_text = data.get('template', '')
        platform = data.get('platform', 'twitter')
        topic = data.get('topic', '')
        tone = data.get('tone', 'professional')
        length = data.get('length', 'medium')
        
        # Generate content using OpenAI
        result = get_content_generator().generate_content(
            template=template_text,
            platform=platform,
            topic=topic,
            tone=tone,
            length=length
        )
        
        # Save to database
        content = GeneratedContent(
            title=result['title'],
            content=result['content'],
            platform=platform,
            status='draft'
        )
        
        db.session.add(content)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'content_id': content.id,
            'title': result['title'],
            'content': result['content'],
            'hashtags': result.get('hashtags', [])
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/library')
def library():
    """Content library page"""
    page = request.args.get('page', 1, type=int)
    status_filter = request.args.get('status', 'all')
    platform_filter = request.args.get('platform', 'all')
    
    query = GeneratedContent.query
    
    if status_filter != 'all':
        query = query.filter_by(status=status_filter)
    
    if platform_filter != 'all':
        query = query.filter_by(platform=platform_filter)
    
    content_items = query.order_by(GeneratedContent.created_at.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    
    platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'blog']
    statuses = ['draft', 'scheduled', 'published', 'failed']
    
    return render_template('library.html', 
                         content_items=content_items,
                         platforms=platforms,
                         statuses=statuses,
                         current_status=status_filter,
                         current_platform=platform_filter)


@app.route('/edit-content/<int:content_id>')
def edit_content(content_id):
    """Edit specific content"""
    content = GeneratedContent.query.get_or_404(content_id)
    return render_template('generate.html', edit_content=content)


@app.route('/api/update-content/<int:content_id>', methods=['POST'])
def api_update_content(content_id):
    """API endpoint to update content"""
    try:
        content = GeneratedContent.query.get_or_404(content_id)
        data = request.get_json()
        
        content.title = data.get('title', content.title)
        content.content = data.get('content', content.content)
        content.platform = data.get('platform', content.platform)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/schedule')
def schedule_page():
    """Scheduling page"""
    scheduled_content = GeneratedContent.query.filter_by(status='scheduled').all()
    draft_content = GeneratedContent.query.filter_by(status='draft').all()
    
    return render_template('schedule.html', 
                         scheduled_content=scheduled_content,
                         draft_content=draft_content)


@app.route('/api/schedule-content', methods=['POST'])
def api_schedule_content():
    """API endpoint to schedule content"""
    try:
        data = request.get_json()
        content_id = data.get('content_id')
        scheduled_time_str = data.get('scheduled_time')
        
        content = GeneratedContent.query.get_or_404(content_id)
        scheduled_time = datetime.fromisoformat(scheduled_time_str.replace('Z', '+00:00'))
        
        # Schedule the content
        job_id = content_scheduler.schedule_post(content_id, scheduled_time)
        
        return jsonify({'success': True, 'job_id': job_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cancel-schedule/<int:content_id>', methods=['POST'])
def api_cancel_schedule(content_id):
    """API endpoint to cancel scheduled content"""
    try:
        content_scheduler.cancel_scheduled_post(content_id)
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/analytics')
def analytics():
    """Analytics dashboard"""
    # Get analytics data
    total_views = db.session.query(db.func.sum(PostAnalytics.views)).scalar() or 0
    total_likes = db.session.query(db.func.sum(PostAnalytics.likes)).scalar() or 0
    total_shares = db.session.query(db.func.sum(PostAnalytics.shares)).scalar() or 0
    total_comments = db.session.query(db.func.sum(PostAnalytics.comments)).scalar() or 0
    
    # Platform performance
    platform_stats = db.session.query(
        PostAnalytics.platform,
        db.func.sum(PostAnalytics.views).label('views'),
        db.func.sum(PostAnalytics.likes).label('likes'),
        db.func.avg(PostAnalytics.engagement_rate).label('avg_engagement')
    ).group_by(PostAnalytics.platform).all()
    
    # Recent posts performance
    recent_analytics = db.session.query(PostAnalytics, GeneratedContent).join(
        GeneratedContent, PostAnalytics.content_id == GeneratedContent.id
    ).order_by(PostAnalytics.recorded_at.desc()).limit(10).all()
    
    return render_template('analytics.html',
                         total_views=total_views,
                         total_likes=total_likes,
                         total_shares=total_shares,
                         total_comments=total_comments,
                         platform_stats=platform_stats,
                         recent_analytics=recent_analytics)


@app.route('/platforms')
def platforms():
    """Platform connections management"""
    connections = PlatformConnection.query.all()
    
    # Ensure all platforms exist in database
    default_platforms = ['twitter', 'facebook', 'instagram', 'linkedin', 'blog']
    existing_platforms = [conn.platform_name for conn in connections]
    
    for platform in default_platforms:
        if platform not in existing_platforms:
            new_conn = PlatformConnection(platform_name=platform, is_connected=False)
            db.session.add(new_conn)
    
    db.session.commit()
    connections = PlatformConnection.query.all()
    
    return render_template('platforms.html', connections=connections)


@app.route('/api/toggle-platform/<int:platform_id>', methods=['POST'])
def api_toggle_platform(platform_id):
    """API endpoint to toggle platform connection"""
    try:
        platform = PlatformConnection.query.get_or_404(platform_id)
        platform.is_connected = not platform.is_connected
        platform.last_used = datetime.utcnow() if platform.is_connected else None
        
        db.session.commit()
        
        return jsonify({'success': True, 'is_connected': platform.is_connected})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/templates')
def api_templates():
    """API endpoint to get templates"""
    templates = ContentTemplate.query.all()
    return jsonify([{
        'id': t.id,
        'name': t.name,
        'description': t.description,
        'template_text': t.template_text,
        'platform': t.platform
    } for t in templates])


@app.route('/api/create-template', methods=['POST'])
def api_create_template():
    """API endpoint to create new template"""
    try:
        data = request.get_json()
        
        template = ContentTemplate(
            name=data.get('name'),
            description=data.get('description'),
            template_text=data.get('template_text'),
            platform=data.get('platform')
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({'success': True, 'template_id': template.id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/analytics-data')
def api_analytics_data():
    """API endpoint for chart data"""
    # Get daily analytics for the last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    daily_stats = db.session.query(
        db.func.date(PostAnalytics.recorded_at).label('date'),
        db.func.sum(PostAnalytics.views).label('views'),
        db.func.sum(PostAnalytics.likes).label('likes'),
        db.func.sum(PostAnalytics.shares).label('shares')
    ).filter(
        PostAnalytics.recorded_at >= thirty_days_ago
    ).group_by(
        db.func.date(PostAnalytics.recorded_at)
    ).all()
    
    return jsonify([{
        'date': stat.date.isoformat(),
        'views': stat.views or 0,
        'likes': stat.likes or 0,
        'shares': stat.shares or 0
    } for stat in daily_stats])


# Initialize some default templates
def create_default_templates():
    if ContentTemplate.query.count() == 0:
        default_templates = [
            {
                'name': 'Product Announcement',
                'description': 'Template for announcing new products or features',
                'template_text': 'Exciting news! We\'re thrilled to announce [PRODUCT/FEATURE]. [BRIEF_DESCRIPTION] This will help you [BENEFIT]. Available [WHEN]. #innovation #product',
                'platform': 'twitter'
            },
            {
                'name': 'Industry Insight',
                'description': 'Share industry knowledge and insights',
                'template_text': 'Industry insight: [INSIGHT]. This trend shows [IMPLICATIONS]. Companies should consider [RECOMMENDATIONS]. What are your thoughts? #industry #insights',
                'platform': 'linkedin'
            },
            {
                'name': 'Behind the Scenes',
                'description': 'Show company culture and team',
                'template_text': 'Behind the scenes at [COMPANY]: [ACTIVITY/EVENT]. Our team is [ACTION/FEELING]. We believe in [VALUES]. #team #culture #behindthescenes',
                'platform': 'instagram'
            },
            {
                'name': 'Educational Content',
                'description': 'Share educational tips and how-tos',
                'template_text': 'Pro tip: [TIP]. Here\'s why this works: [EXPLANATION]. Try this method: [STEPS]. Let us know how it goes! #tips #education #howto',
                'platform': 'facebook'
            }
        ]
        
        for template_data in default_templates:
            template = ContentTemplate(**template_data)
            db.session.add(template)
        
        db.session.commit()
