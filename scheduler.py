import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from app import app, db
from models import GeneratedContent, PostAnalytics, PlatformConnection
import random


class ContentScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logging.info("Content scheduler initialized")
    
    def schedule_post(self, content_id, scheduled_time):
        """
        Schedule a post for publishing at specified time
        """
        try:
            with app.app_context():
                content = GeneratedContent.query.get(content_id)
                if not content:
                    raise Exception("Content not found")
                
                # Schedule the job
                job_id = f"post_{content_id}_{int(scheduled_time.timestamp())}"
                
                self.scheduler.add_job(
                    func=self._publish_content,
                    trigger=DateTrigger(run_date=scheduled_time),
                    args=[content_id],
                    id=job_id,
                    name=f"Publish: {content.title}"
                )
                
                # Update content status
                content.scheduled_for = scheduled_time
                content.status = 'scheduled'
                db.session.commit()
                
                logging.info(f"Scheduled content {content_id} for {scheduled_time}")
                return job_id
                
        except Exception as e:
            logging.error(f"Failed to schedule post: {str(e)}")
            raise
    
    def cancel_scheduled_post(self, content_id):
        """
        Cancel a scheduled post
        """
        try:
            with app.app_context():
                content = GeneratedContent.query.get(content_id)
                if not content:
                    raise Exception("Content not found")
                
                # Find and remove the job
                jobs = self.scheduler.get_jobs()
                for job in jobs:
                    if job.id.startswith(f"post_{content_id}_"):
                        self.scheduler.remove_job(job.id)
                        break
                
                # Update content status
                content.status = 'draft'
                content.scheduled_for = None
                db.session.commit()
                
                logging.info(f"Cancelled scheduled post for content {content_id}")
                
        except Exception as e:
            logging.error(f"Failed to cancel scheduled post: {str(e)}")
            raise
    
    def _publish_content(self, content_id):
        """
        Publish content to the specified platform (mock implementation)
        """
        try:
            with app.app_context():
                content = GeneratedContent.query.get(content_id)
                if not content:
                    logging.error(f"Content {content_id} not found")
                    return
                
                # Check if platform is connected
                platform_conn = PlatformConnection.query.filter_by(
                    platform_name=content.platform
                ).first()
                
                if not platform_conn or not platform_conn.is_connected:
                    content.status = 'failed'
                    db.session.commit()
                    logging.error(f"Platform {content.platform} not connected")
                    return
                
                # Mock publication (in real implementation, this would call actual APIs)
                success = self._mock_publish_to_platform(content)
                
                if success:
                    content.status = 'published'
                    content.published_at = datetime.utcnow()
                    
                    # Generate mock analytics data
                    self._generate_mock_analytics(content)
                    
                    logging.info(f"Successfully published content {content_id}")
                else:
                    content.status = 'failed'
                    logging.error(f"Failed to publish content {content_id}")
                
                db.session.commit()
                
        except Exception as e:
            logging.error(f"Error publishing content {content_id}: {str(e)}")
    
    def _mock_publish_to_platform(self, content):
        """
        Mock platform publishing (for MVP)
        In real implementation, this would integrate with actual platform APIs
        """
        # Simulate success/failure (90% success rate)
        success_rate = 0.9
        return random.random() < success_rate
    
    def _generate_mock_analytics(self, content):
        """
        Generate mock analytics data for published content
        """
        try:
            # Generate realistic mock data based on platform
            platform_multipliers = {
                'twitter': {'views': 100, 'likes': 10, 'shares': 5, 'comments': 3},
                'facebook': {'views': 150, 'likes': 15, 'shares': 8, 'comments': 5},
                'instagram': {'views': 200, 'likes': 25, 'shares': 12, 'comments': 8},
                'linkedin': {'views': 80, 'likes': 8, 'shares': 4, 'comments': 2},
                'blog': {'views': 300, 'likes': 20, 'shares': 10, 'comments': 15}
            }
            
            multiplier = platform_multipliers.get(content.platform, platform_multipliers['twitter'])
            
            analytics = PostAnalytics(
                content_id=content.id,
                platform=content.platform,
                views=random.randint(multiplier['views']//2, multiplier['views']*2),
                likes=random.randint(multiplier['likes']//2, multiplier['likes']*2),
                shares=random.randint(multiplier['shares']//2, multiplier['shares']*2),
                comments=random.randint(multiplier['comments']//2, multiplier['comments']*2)
            )
            
            # Calculate engagement rate
            if analytics.views > 0:
                engagement = (analytics.likes + analytics.shares + analytics.comments) / analytics.views
                analytics.engagement_rate = round(engagement * 100, 2)
            
            db.session.add(analytics)
            db.session.commit()
            
        except Exception as e:
            logging.error(f"Failed to generate analytics: {str(e)}")
    
    def get_scheduled_jobs(self):
        """
        Get all scheduled jobs
        """
        jobs = self.scheduler.get_jobs()
        return [
            {
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    
    def shutdown(self):
        """
        Shutdown the scheduler
        """
        self.scheduler.shutdown()


# Initialize global scheduler
content_scheduler = ContentScheduler()
