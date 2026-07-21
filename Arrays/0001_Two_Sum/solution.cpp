// 1. Two Sum
// Difficulty: Easy
// Link: https://leetcode.com/problems/two-sum/
// Runtime: 36 ms | Memory: 14 MB

class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        int n = nums.size();

        for (int i = 0; i < n; i++) {
            for (int j = i + 1; j < n; j++) {
                if (nums[i] + nums[j] == target) {
                    return {i,j};
                } 
            }
        }
        return {};
    }
};
