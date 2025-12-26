export interface ChannelStats {
    subscriberCount: number;
    viewCount: number;
    videoCount: number;
    watchTimeHours: number;
    avgEngagementRate: number;
    profileImage?: string;
    revenue: number;
    likes: number; // Added
    lastUpdated?: string;
}

export interface VideoData {
    id: string;
    title: string;
    thumbnail: string;
    publishedAt: string;
    views: number;
    likes: number;
    dislikes: number;
    revenue: number;
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
    text: string;
    date: string;
    likes: number;
    videoTitle: string;
}

export type AppTab = 'Dashboard' | 'Content' | 'Analytics' | 'Comments' | 'Earn' | 'Customization';

// New types for Real Data
//    estimatedMinutesWatched?: number[];
export interface AIInsightItem {
    title: string;
    content: string;
}

export interface InsightItem {
    title: string;
    content: string;
}

export interface CurrentAnalysis {
    strengths: InsightItem;
    improvements: InsightItem;
    action_plan: InsightItem;
    detailed_report?: string;
}

export interface FutureStrategy {
    growth_trend: InsightItem;
    risk_factor: InsightItem;
    action_strategy: InsightItem;
    detailed_report?: string;
}

export interface AIInsights {
    current_analysis: CurrentAnalysis;
    future_strategy: FutureStrategy;
}

export interface PredictionData {
    last_updated: string;
    dates: string[];
    predictions: {
        ma: {
            view_count: number[];
            subscriber_count: number[];
            revenue: number[];
            watch_time: number[];
            likes: number[];
            dislikes: number[];
        };
        wma: {
            view_count: number[];
            subscriber_count: number[];
            revenue: number[];
            watch_time: number[];
            likes: number[];
            dislikes: number[];
        };
        xgboost: {
            view_count: number[];
            subscriber_count: number[];
            revenue: number[];
            watch_time: number[];
            likes: number[];
            dislikes: number[];
        };
    };
}

export interface DashboardData {
    summary: {
        channel_name: string;
        profile_image: string;
        total_views_30d: number;
        estimated_revenue_30d: number;
        subs_gained_30d: number;
        total_watch_time_hours_30d: number;
        likes_30d: number;
        avg_engagement_rate_30d: number;
        last_updated: string;
    };
    trends: {
        daily: TrendData;
        weekly: TrendData;
        monthly: TrendData;
    };
    prediction: {
        dates: string[];
        views: number[];
    };
    ai_insights?: AIInsights;
    top_videos: VideoData[];
    comments: CommentData[];
    demographics: {
        age_gender: {
            headers: string[];
            rows: (string | number)[][];
        };
        geography: {
            headers: string[];
            rows: (string | number)[][];
        };
    };
};
traffic_sources: {
    insightTrafficSourceType: string;
    views: number;
    estimatedMinutesWatched: number;
} [];
}

export interface TrendData {
    dates: string[];
    views: number[];
    revenue: number[];
    subscribers: number[];
    averageViewDuration: number[];
    estimatedMinutesWatched: number[];
}
