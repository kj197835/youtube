import React from 'react';
import { VideoData } from '../types';

interface VideoGridProps {
    videos: VideoData[];
}

const VideoGrid: React.FC<VideoGridProps> = ({ videos }) => {
    return (
        <div className="space-y-4">
            <h2 className="text-xl font-bold text-gray-800">Recent Content</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {videos.map((video) => (
                    <div key={video.id} className="bg-white rounded-2xl overflow-hidden border border-gray-100 group shadow-sm hover:shadow-md transition-all">
                        <div className="relative aspect-video bg-gray-200">
                            <img src={video.thumbnail} alt={video.title} className="w-full h-full object-cover" onError={(e) => (e.currentTarget.src = "https://placehold.co/600x400?text=No+Thumbnail")} />
                        </div>
                        <div className="p-4">
                            <h3 className="font-semibold text-gray-900 line-clamp-2 leading-tight h-10 mb-2">{video.title}</h3>
                            <div className="flex justify-between items-center text-xs text-gray-500">
                                <span>{video.views.toLocaleString()} views</span>
                                <span className={`px-2 py-1 rounded-full font-bold ${video.status === 'Public' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                    {video.status}
                                </span>
                            </div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default VideoGrid;
