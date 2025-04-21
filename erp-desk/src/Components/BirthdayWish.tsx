import { useEffect, useState } from 'react';
import Confetti from 'react-confetti';
import { motion, AnimatePresence } from 'framer-motion';
import { useSelector } from 'react-redux';
import { RootState } from '../Store';

const BirthdayBlast: React.FC<any> = ({ setShowBlast }) => {
    const [windowSize, setWindowSize] = useState({ width: 0, height: 0 });
    const { userData } = useSelector((state: RootState) => state.user);

    useEffect(() => {
        const updateSize = () => {
            setWindowSize({ width: window.innerWidth, height: window.innerHeight });
        };

        updateSize(); // Initial size
        window.addEventListener('resize', updateSize);


        return () => {
            window.removeEventListener('resize', updateSize);
        };
    }, []);
    return (
        <AnimatePresence>
            <motion.div
                className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-black/80 px-4"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
            >
                <Confetti width={windowSize.width} height={windowSize.height} />

                <motion.div
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ duration: 0.8, type: 'spring' }}
                    className="text-center text-white"
                >
                    <h1 className="text-3xl sm:text-4xl md:text-6xl font-extrabold leading-tight">
                        {userData?.is_anniversary && "🎉 Happy Anniversary!"}
                        {userData?.is_birthday && "🎂 Happy Birthday!"}
                        
                    </h1>
                    <p className="mt-3 text-base sm:text-lg md:text-2xl">
                        Wishing you a day full of fun and surprises!
                    </p>

                    <button
                        onClick={() => setShowBlast(false)}
                        className="mt-6 bg-pink-600 cursor-pointer hover:bg-pink-700 text-white px-5 py-2 rounded-full text-sm sm:text-base transition duration-300 ease-in-out"
                    >
                        Close
                    </button>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
};

export default BirthdayBlast;
