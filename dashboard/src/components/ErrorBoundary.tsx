import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
    children?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error("Uncaught error:", error, errorInfo);
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-4">
                    <div className="bg-white p-8 rounded-lg shadow-md max-w-lg w-full text-center">
                        <h1 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
                        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 overflow-auto max-h-60 text-left">
                            <p className="font-mono text-sm text-red-800 whitespace-pre-wrap">
                                {this.state.error?.message}
                            </p>
                            <p className="font-mono text-xs text-red-600 mt-2">
                                {this.state.error?.stack?.split('\n')[0]}
                            </p>
                        </div>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                        >
                            Reload Page
                        </button>
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
