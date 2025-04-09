import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@mui/material';
import nodata from '../Assets/no-data.gif'
const PageNotFound: React.FC = () => {
    const navigate = useNavigate();

    return (
        <div className="flex flex-col items-center justify-center min-h-screen bg-[#f9fafb] px-4">
            <img
                src={nodata}
                alt="404 Not Found"
                className="max-w-xs md:max-w-sm mb-6"
            />
            <h2 className="text-2xl md:text-3xl font-semibold text-[#181D27] mb-2">
                Oops! Page Not Found
            </h2>
            <p className="text-[#6b7280] mb-6 text-center">
                The page you're looking for doesn't exist or has been moved.
            </p>
            <Button
                onClick={() => navigate('/login')}
                className="!rounded-xl !px-6 !py-2 !bg-[#4d8c52] !text-[#fff]"
            >
                Go to Login
            </Button>
        </div>
    );
};

export default PageNotFound;
