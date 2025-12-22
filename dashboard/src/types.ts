export interface ChannelStats {
    subscriberCount: number;
    viewCount: number;
    videoCount: number;
    watchTimeHours: number;
    avgEngagementRate: number;
    profileImage?: string;
    revenue: number; // Added
    lastUpdated?: string;
}

export interface VideoData {
    id: string;
    title: string;
    thumbnail: string;
    publishedAt: string;
    views: number;
    likes: number;
    dislikes: number; // Added
    revenue: number; // Added
    comments: number;
    retentionRate: number;
    status: 'Public' | 'Unlisted' | 'Private';
}

export interface AIInsight {
    topic: string;
    analysis: string;
    recommendation: string;
    impact: 'High' | 'Medium' | 'Low';
}

export interface ChartData {
    name: string;
    views: number;
    subscribers: number;
    revenue?: number;
    likes?: number;
    dislikes?: number;
    watchTime?: number;
}

export interface CommentData {
    id: string;
    author: string;
    avatar: string;
    text: string;
    timestamp: string;
    likes: number;
    videoTitle: string;
}

export type AppTab = 'Dashboard' | 'Content' | 'Analytics' | 'Comments' | 'Earn' | 'Customization';

// New types for Real Data
export interface DashboardData {
    summary: {
        channel_name?: string;
        profile_image?: string;
        total_views_30d: number;
        estimated_revenue_30d: number;
        subs_gained_30d: number;
        total_watch_time_hours_30d?: number;
        avg_engagement_rate_30d?: number; // Added field
        last_updated: string;
    };
    trends: {
        daily: TrendData;
        weekly: TrendData;
        monthly: TrendData;
    };
    top_videos: Array<{
        video: string;
        views: number;
        estimatedMinutesWatched: number;
        estimatedRevenue: number;
        subscribersGained: number;
    }>;
    demographics: {
        age_gender?: {
            headers: string[];
            rows: Array<[string, string, number]>;
        };
        geography?: {
            headers: string[];
            rows: Array<[string, number, number]>;
        };
    };
    traffic_sources?: Array<{
        insightTrafficSourceType: string;
        views: number;
        estimatedMinutesWatched: number;
    }>;
}

export interface TrendData {
    dates: string[];
    views: number[];
    revenue: number[];
    subscribers: number[];
    averageViewDuration: number[];
}
